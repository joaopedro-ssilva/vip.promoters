"""Revogacao de sessoes: a familia do refresh token (sid no JWT) e marcada como revogada."""

import logging
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models import RefreshToken

log = logging.getLogger("app.sessions")
_PREFIX = "revoked_sid:"


def _key(sid: uuid.UUID) -> str:
    return f"{_PREFIX}{sid}"


def lock_key(family_id: uuid.UUID) -> int:
    return int.from_bytes(family_id.bytes[:8], "big", signed=True)


async def lock_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    """Serializa refresh/logout/revogacao da mesma familia (libera no fim da transacao)."""
    await db.execute(select(func.pg_advisory_xact_lock(lock_key(family_id))))


async def lock_families(db: AsyncSession, family_ids: Iterable[uuid.UUID]) -> None:
    for fid in sorted(set(family_ids), key=lock_key):  # ordem fixa evita deadlock
        await lock_family(db, fid)


async def mark_revoked(sids: Iterable[uuid.UUID]) -> None:
    """Marca as familias como revogadas no Redis pelo tempo de vida do access token."""
    ttl = settings.access_token_minutes * 60 + 60
    try:
        pipe = get_redis().pipeline()
        count = 0
        for sid in sids:
            pipe.set(_key(sid), "1", ex=ttl)
            count += 1
        if count:
            await pipe.execute()
    except Exception:  # noqa: BLE001
        log.error("nao foi possivel marcar sessoes como revogadas", extra={"event": "revoke"})


async def is_revoked(db: AsyncSession, sid: uuid.UUID) -> bool:
    """Redis primeiro; se indisponivel, consulta o Postgres. Falha fechada: na duvida, revoga."""
    try:
        return bool(await get_redis().exists(_key(sid)))
    except Exception:  # noqa: BLE001
        live = await db.scalar(
            select(
                exists().where(
                    RefreshToken.family_id == sid,
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > datetime.now(UTC),
                )
            )
        )
        return not live
