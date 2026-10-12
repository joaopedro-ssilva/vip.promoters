"""Middlewares ASGI: limite de corpo, CSRF, cabecalhos de seguranca, request id e log."""

import json
import logging
import time
import uuid

from fastapi import HTTPException
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.core.errors import error_body, security_headers
from app.core.security import ACCESS_COOKIE, decode_access_token

access_log = logging.getLogger("app.access")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_EXEMPT_PREFIXES = ("/api/v1/webhooks/", "/api/v1/meta/")
UPLOAD_PATH = "/api/v1/uploads/image"
UPLOAD_MAX_BODY = 9 * 1024 * 1024  # 8 MB do arquivo + envelope multipart
DEFAULT_MAX_BODY = 1024 * 1024  # webhooks e todas as outras rotas


async def _send_json(
    send: Send, status: int, code: str, message: str, extra: list[tuple[bytes, bytes]] | None = None
) -> None:
    body = json.dumps(error_body(code, message), ensure_ascii=False).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"x-content-type-options", b"nosniff"),
                (b"cache-control", b"no-store"),
                *(extra or []),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class BodyLimitMiddleware:
    """Limita o tamanho do corpo ENQUANTO ele e recebido (inclusive chunked) e recusa
    uploads sem sessao antes de qualquer byte ser lido."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        path: str = scope["path"]
        limit = UPLOAD_MAX_BODY if path == UPLOAD_PATH else DEFAULT_MAX_BODY
        headers = Headers(scope=scope)
        if path == UPLOAD_PATH:
            cookie_header = headers.get("cookie", "")
            token = None
            for part in cookie_header.split(";"):
                name, _, value = part.strip().partition("=")
                if name == ACCESS_COOKIE:
                    token = value
            if not token or decode_access_token(token) is None:
                await _send_json(send, 401, "unauthenticated", "Faça login para continuar.")
                return
        declared = headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            await _send_json(send, 413, "payload_too_large", "Conteúdo grande demais.")
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # HTTPException passa pelo FastAPI e vira o envelope 413 padrao
                    raise HTTPException(413)
            return message

        await self.app(scope, limited_receive, send)


class CSRFMiddleware:
    """Exige X-Requested-With e valida Origin (quando presente) em requisicoes que mudam estado."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope["path"]
        method: str = scope["method"]
        if (
            method not in SAFE_METHODS
            and path.startswith("/api/v1")
            and not path.startswith(CSRF_EXEMPT_PREFIXES)
        ):
            headers = Headers(scope=scope)
            origin = headers.get("origin")
            ok = headers.get("x-requested-with") == "XMLHttpRequest"
            if ok and origin is not None and origin.rstrip("/") not in settings.origins:
                ok = False
            if not ok:
                await _send_json(
                    send, 403, "csrf_failed", "Requisição bloqueada por segurança (CSRF)."
                )
                return
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope["path"]
        request_id = uuid.uuid4().hex[:16]
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_holder = {"status": 0}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = MutableHeaders(scope=message)
                for k, v in security_headers(path, request_id).items():
                    headers[k] = v
                if "cache-control" not in headers and not path.startswith("/api/v1/uploads/"):
                    headers["Cache-Control"] = "no-store"
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if not path.startswith("/api/v1/health"):
                access_log.info(
                    "request",
                    extra={
                        "request_id": request_id,
                        "method": scope["method"],
                        "path": path,  # sem query string (pode conter code/state OAuth)
                        "status": status_holder["status"],
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                )
