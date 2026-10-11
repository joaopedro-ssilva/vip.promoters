"""Callbacks da Meta: webhook do Instagram, desautorizacao e exclusao de dados."""

import base64
import hashlib
import hmac
import json
import logging
import secrets
from typing import Any

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import delete, update

from app.api.deps import DB
from app.core.config import settings
from app.core.errors import AppError
from app.models import InstagramAccount, PromoterProfile
from app.services.webhooks import sanitize_payload, verify_signature

log = logging.getLogger("app.webhooks")
router = APIRouter(tags=["meta"])

MAX_WEBHOOK_BYTES = 1_000_000


@router.get("/webhooks/instagram", response_class=PlainTextResponse)
async def verify_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge", max_length=512),
):
    expected = settings.meta_webhook_verify_token
    if (
        mode == "subscribe"
        and expected
        and token is not None
        and hmac.compare_digest(token.encode(), expected.encode())
        and challenge is not None
    ):
        return PlainTextResponse(challenge)
    raise AppError(403, "forbidden", "Verificação do webhook recusada.")


@router.post("/webhooks/instagram")
async def receive_webhook(request: Request):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_WEBHOOK_BYTES:
        raise AppError(413, "payload_too_large", "Conteúdo grande demais.")
    body = await request.body()  # corpo cru: a assinatura vale sobre os bytes exatos
    if len(body) > MAX_WEBHOOK_BYTES or not verify_signature(
        body, request.headers.get("x-hub-signature-256")
    ):
        raise AppError(403, "forbidden", "Assinatura inválida.")
    try:
        payload = json.loads(body)
    except ValueError:
        raise AppError(400, "bad_request", "JSON inválido.") from None
    reduced = sanitize_payload(payload)
    if reduced is None:
        return {"status": "ok"}  # nada que o pipeline processe: descarta
    arq = getattr(request.app.state, "arq", None)
    if arq is None:
        raise AppError(503, "unavailable", "Fila indisponível. Tente novamente.")
    try:
        await arq.enqueue_job("process_webhook", reduced)
    except Exception:
        log.exception("falha ao enfileirar webhook", extra={"event": "enqueue"})
        raise AppError(503, "unavailable", "Fila indisponível. Tente novamente.") from None
    return {"status": "ok"}


def _parse_signed_request(signed_request: str) -> dict[str, Any]:
    secret = settings.webhook_secret
    try:
        sig_b64, payload_b64 = signed_request.split(".", 1)
        sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
        expected = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
        if not secret or not hmac.compare_digest(sig, expected):
            raise ValueError("assinatura")
        data = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
        if not isinstance(data, dict):
            raise ValueError("payload")
        return data
    except (ValueError, TypeError):
        raise AppError(403, "forbidden", "signed_request inválido.") from None


@router.post("/meta/deauthorize")
async def deauthorize(db: DB, signed_request: str = Form(..., max_length=4096)):
    data = _parse_signed_request(signed_request)
    user_id = str(data.get("user_id") or "")
    if user_id:
        await db.execute(
            update(InstagramAccount)
            .where(InstagramAccount.ig_user_id == user_id)
            .values(status="revoked")
        )
        await db.commit()
    return {"status": "ok"}


@router.post("/meta/data-deletion")
async def data_deletion(db: DB, signed_request: str = Form(..., max_length=4096)):
    data = _parse_signed_request(signed_request)
    user_id = str(data.get("user_id") or "")
    if user_id:
        await db.execute(delete(InstagramAccount).where(InstagramAccount.ig_user_id == user_id))
        await db.execute(
            update(PromoterProfile)
            .where(PromoterProfile.ig_scoped_id == user_id)
            .values(ig_scoped_id=None, verified=False, verified_at=None, verification_method=None)
        )
        await db.commit()
    code = secrets.token_urlsafe(12)
    return {
        "url": f"{settings.app_base_url}/api/v1/meta/data-deletion/{code}",
        "confirmation_code": code,
    }


@router.get("/meta/data-deletion/{code}")
async def data_deletion_status(code: str):
    return {"status": "completed", "confirmation_code": code[:64]}
