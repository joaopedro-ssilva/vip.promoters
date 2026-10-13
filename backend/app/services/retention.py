"""Politica de retencao (LGPD: minimizacao e prazo de guarda).

O que o app guarda de terceiros sao os comentarios e mencoes em story: texto, @, id do
Instagram e link da midia. Isso so serve enquanto a campanha esta viva (pontuar, conferir,
re-casar ao aprovar um promoter). Depois de RETENTION_DAYS do encerramento, a interacao e
ANONIMIZADA: some o que identifica a pessoa, ficam tipo, data, status e pontos — o extrato do
promoter e os numeros do gestor continuam batendo.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Campaign, Interaction, Notification, RefreshToken
from app.models.base import CampaignStatus

log = logging.getLogger("app.retention")

# Sessao revogada fica um tempo para a deteccao de reuso de refresh token funcionar.
REVOKED_SESSION_GRACE = timedelta(days=30)

PERSONAL_FIELDS = {"text": None, "ig_username": None, "ig_scoped_id": None, "media_url": None}


def _has_personal_data():
    return or_(
        Interaction.text.is_not(None),
        Interaction.ig_username.is_not(None),
        Interaction.ig_scoped_id.is_not(None),
        Interaction.media_url.is_not(None),
    )


@dataclass
class PurgeResult:
    interactions_anonymized: int = 0
    refresh_tokens_deleted: int = 0
    notifications_deleted: int = 0


async def anonymize_old_interactions(db: AsyncSession, now: datetime | None = None) -> int:
    """Anonimiza interacoes de campanhas encerradas ha mais de RETENTION_DAYS e as sem
    campanha (mencao fora de periodo) mais antigas que isso. Nao faz commit."""
    if settings.retention_days <= 0:
        return 0
    cutoff = (now or datetime.now(UTC)) - timedelta(days=settings.retention_days)
    ended_long_ago = select(Campaign.id).where(
        Campaign.status == CampaignStatus.ended.value,
        Campaign.ended_at.is_not(None),
        Campaign.ended_at < cutoff,
    )
    res = await db.execute(
        update(Interaction)
        .where(
            _has_personal_data(),
            or_(
                Interaction.campaign_id.in_(ended_long_ago),
                and_(Interaction.campaign_id.is_(None), Interaction.occurred_at < cutoff),
            ),
        )
        .values(**PERSONAL_FIELDS)
        .execution_options(synchronize_session=False)
    )
    return res.rowcount or 0


async def purge(db: AsyncSession, now: datetime | None = None) -> PurgeResult:
    """Retencao completa. Faz commit."""
    now = now or datetime.now(UTC)
    out = PurgeResult()
    out.interactions_anonymized = await anonymize_old_interactions(db, now)
    res = await db.execute(
        delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < now,
                RefreshToken.revoked_at < now - REVOKED_SESSION_GRACE,
            )
        )
    )
    out.refresh_tokens_deleted = res.rowcount or 0
    if settings.notification_retention_days > 0:
        res = await db.execute(
            delete(Notification).where(
                Notification.read_at.is_not(None),
                Notification.created_at
                < now - timedelta(days=settings.notification_retention_days),
            )
        )
        out.notifications_deleted = res.rowcount or 0
    await db.commit()
    log.info(
        "retencao: %d interacoes anonimizadas, %d sessoes e %d notificacoes apagadas",
        out.interactions_anonymized,
        out.refresh_tokens_deleted,
        out.notifications_deleted,
        extra={"event": "retention"},
    )
    return out
