"""Envelope de erro unico com as chaves error.code, error.message e error.fields (opcional)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

log = logging.getLogger("app.errors")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields
        self.headers = headers


def not_found(message: str = "Recurso não encontrado.") -> AppError:
    return AppError(404, "not_found", message)


def bad_request(code: str, message: str) -> AppError:
    return AppError(400, code, message)


def error_body(code: str, message: str, fields: dict[str, str] | None = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if fields:
        err["fields"] = fields
    return {"error": err}


DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


def security_headers(path: str, request_id: str | None = None) -> dict[str, str]:
    """Cabecalhos de seguranca comuns a TODAS as respostas (inclusive erros 500)."""
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }
    if not path.startswith(DOCS_PATHS):
        headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    if settings.cookie_secure:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


def error_response(
    status: int,
    code: str,
    message: str,
    fields: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    *,
    path: str = "/",
    request_id: str | None = None,
) -> JSONResponse:
    merged = {
        **SECURITY_HEADERS,
        **security_headers(path, request_id),
        **(headers or {}),
    }
    return JSONResponse(error_body(code, message, fields), status_code=status, headers=merged)


_HTTP_CODES = {
    400: ("bad_request", "Requisição inválida."),
    401: ("unauthenticated", "Faça login para continuar."),
    403: ("forbidden", "Você não tem permissão para isso."),
    404: ("not_found", "Recurso não encontrado."),
    405: ("method_not_allowed", "Método não permitido."),
    409: ("conflict", "Conflito com o estado atual do recurso."),
    413: ("payload_too_large", "Conteúdo grande demais."),
    415: ("unsupported_media_type", "Tipo de conteúdo não suportado."),
    429: ("rate_limited", "Muitas tentativas. Tente novamente em instantes."),
}


def _validation_message(err: dict[str, Any]) -> str:
    t = err.get("type", "")
    ctx = err.get("ctx") or {}
    if t == "missing":
        return "Campo obrigatório."
    if t == "value_error":
        inner = ctx.get("error")
        text = str(inner) if inner is not None else err.get("msg", "")
        return text.removeprefix("Value error, ") or "Valor inválido."
    if t == "string_too_short":
        return f"Muito curto (mínimo {ctx.get('min_length')} caracteres)."
    if t == "string_too_long":
        return f"Muito longo (máximo {ctx.get('max_length')} caracteres)."
    if t in ("int_parsing", "int_from_float", "float_parsing", "int_type"):
        return "Informe um número válido."
    if t in ("greater_than", "greater_than_equal"):
        return f"O valor deve ser maior ou igual a {ctx.get('ge', ctx.get('gt'))}."
    if t in ("less_than", "less_than_equal"):
        return f"O valor deve ser menor ou igual a {ctx.get('le', ctx.get('lt'))}."
    if t in ("literal_error", "enum"):
        return "Valor inválido."
    if t in ("uuid_parsing", "uuid_type"):
        return "Identificador inválido."
    if t in ("string_type", "bool_parsing", "bool_type", "dict_type", "list_type"):
        return "Tipo de valor inválido."
    if t.startswith("datetime") or t.startswith("date"):
        return "Data/hora inválida."
    if t == "json_invalid":
        return "JSON inválido."
    if t == "too_short":
        return "Informe ao menos um item."
    return "Valor inválido."


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts) or "body"


def _ctx(request: Request) -> dict[str, Any]:
    return {
        "path": request.url.path,
        "request_id": request.scope.get("state", {}).get("request_id"),
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            exc.status_code, exc.code, exc.message, exc.fields, exc.headers, **_ctx(request)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            fields.setdefault(_field_name(tuple(err.get("loc", ()))), _validation_message(err))
        return error_response(422, "validation_error", "Dados inválidos.", fields, **_ctx(request))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _HTTP_CODES.get(exc.status_code, ("error", "Erro na requisição."))
        headers = {k: v for k, v in (exc.headers or {}).items() if k.lower() == "allow"}
        return error_response(
            exc.status_code, code, message, headers=headers or None, **_ctx(request)
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled exception", exc_info=exc, extra={"event": "unhandled"})
        return error_response(
            500, "internal_error", "Erro interno. Tente novamente mais tarde.", **_ctx(request)
        )
