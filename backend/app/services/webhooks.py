"""Verificacao de assinatura da Meta e traducao de payloads em InboundEvent."""

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from redis.exceptions import RedisError
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.instagram.base import (
    InstagramAuthError,
    InstagramError,
    InstagramRateLimitError,
)
from app.services.interactions import InboundEvent, TransientPipelineError, process_event

log = logging.getLogger("app.webhooks")


def sign_body(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, header: str | None) -> bool:
    secret = settings.webhook_secret
    if not secret or not header or not header.startswith("sha256="):
        return False
    return hmac.compare_digest(sign_body(body, secret), header)


def _ts(value: Any, *, millis: bool, default: datetime) -> datetime:
    try:
        n = float(value)
        return datetime.fromtimestamp(n / 1000 if millis else n, UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return default


def parse_payload(payload: dict[str, Any]) -> list[InboundEvent]:
    """Aceita changes[] (field=comments) e messaging[] (story_mention). Ignora o resto."""
    events: list[InboundEvent] = []
    if not isinstance(payload, dict) or payload.get("object") != "instagram":
        return events
    now = datetime.now(UTC)
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "")
        if not entry_id:
            continue
        entry_time = _ts(entry.get("time"), millis=False, default=now)
        for change in entry.get("changes") or []:
            if not isinstance(change, dict) or change.get("field") != "comments":
                continue
            v = change.get("value") or {}
            frm = v.get("from") or {}
            media = v.get("media") or {}
            if not v.get("id") or not media.get("id"):
                continue
            events.append(
                InboundEvent(
                    type="comment",
                    ig_event_id=str(v["id"]),
                    account_ig_id=entry_id,
                    occurred_at=entry_time,
                    from_id=str(frm["id"]) if frm.get("id") else None,
                    from_username=frm.get("username"),
                    media_id=str(media["id"]),
                    text=v.get("text"),
                    parent_id=str(v["parent_id"]) if v.get("parent_id") else None,
                )
            )
        for msg in entry.get("messaging") or []:
            if not isinstance(msg, dict):
                continue
            message = msg.get("message") or {}
            if not isinstance(message, dict) or message.get("is_echo"):
                continue
            sender = (msg.get("sender") or {}).get("id")
            mid = message.get("mid")
            if not mid or not sender or str(sender) == entry_id:
                continue
            for att in message.get("attachments") or []:
                if isinstance(att, dict) and att.get("type") == "story_mention":
                    url = (att.get("payload") or {}).get("url")
                    events.append(
                        InboundEvent(
                            type="story_mention",
                            ig_event_id=str(mid),
                            account_ig_id=entry_id,
                            occurred_at=_ts(msg.get("timestamp"), millis=True, default=now),
                            from_id=str(sender),
                            media_url=url if isinstance(url, str) else None,
                        )
                    )
                    break
    return events


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Reduz o payload ao estritamente necessario ao pipeline antes de enfileirar:
    comentarios (campo comments) e mensagens com anexo story_mention (so ids, timestamp, mid e
    URL do anexo). Todo o resto (texto de mensagens privadas etc.) e descartado."""
    if not isinstance(payload, dict) or payload.get("object") != "instagram":
        return None
    entries_out: list[dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        changes_out = []
        for change in entry.get("changes") or []:
            if not isinstance(change, dict) or change.get("field") != "comments":
                continue
            v = change.get("value") or {}
            if not isinstance(v, dict):
                continue
            frm = v.get("from") or {}
            media = v.get("media") or {}
            changes_out.append(
                {
                    "field": "comments",
                    "value": {
                        "id": v.get("id"),
                        "parent_id": v.get("parent_id"),
                        "text": v.get("text"),
                        "from": {"id": frm.get("id"), "username": frm.get("username")},
                        "media": {"id": media.get("id")},
                    },
                }
            )
        messaging_out = []
        for msg in entry.get("messaging") or []:
            if not isinstance(msg, dict):
                continue
            message = msg.get("message") or {}
            if not isinstance(message, dict) or message.get("is_echo"):
                continue
            atts = [
                {"type": "story_mention", "payload": {"url": (a.get("payload") or {}).get("url")}}
                for a in message.get("attachments") or []
                if isinstance(a, dict) and a.get("type") == "story_mention"
            ]
            if not atts:
                continue
            messaging_out.append(
                {
                    "sender": {"id": (msg.get("sender") or {}).get("id")},
                    "recipient": {"id": (msg.get("recipient") or {}).get("id")},
                    "timestamp": msg.get("timestamp"),
                    "message": {"mid": message.get("mid"), "attachments": atts[:1]},
                }
            )
        if changes_out or messaging_out:
            entries_out.append(
                {
                    "id": entry["id"],
                    "time": entry.get("time"),
                    "changes": changes_out,
                    "messaging": messaging_out,
                }
            )
    if not entries_out:
        return None
    return {"object": "instagram", "entry": entries_out}


_TRANSIENT_SQLSTATES = {"40001", "40P01", "55P03", "57P01", "08000", "08003", "08006"}


def is_transient(exc: BaseException) -> bool:
    """Falhas temporarias que merecem nova tentativa do job."""
    if isinstance(exc, TransientPipelineError | TimeoutError | ConnectionError):
        return True
    if isinstance(exc, RedisError):
        return True
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, InstagramError):
        return not isinstance(exc, InstagramAuthError) and (
            isinstance(exc, InstagramRateLimitError) or exc.status is None or exc.status >= 500
        )
    if isinstance(exc, DBAPIError):
        if exc.connection_invalidated or isinstance(exc, OperationalError | InterfaceError):
            return True
        return getattr(exc.orig, "sqlstate", None) in _TRANSIENT_SQLSTATES
    return False


def event_ids(payload: dict[str, Any]) -> list[str]:
    """Ids de eventos para log (nunca o conteudo)."""
    try:
        return [f"{e.type}:{e.ig_event_id}" for e in parse_payload(payload)]
    except Exception:  # noqa: BLE001
        return []


async def handle_webhook_payload(payload: dict[str, Any]) -> int:
    """Processa um payload ja autenticado. Cada evento usa sua propria sessao/transacao."""
    count = 0
    for ev in parse_payload(payload):
        async with SessionLocal() as db:
            try:
                res = await process_event(db, ev)
                if res.outcome == "created":
                    count += 1
            except Exception:
                log.exception("falha ao processar evento", extra={"event": ev.type})
                raise
    return count
