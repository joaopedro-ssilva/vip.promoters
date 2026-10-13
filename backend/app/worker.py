"""Worker arq: webhooks, polling de comentarios, encerramento de campanhas e refresh de tokens."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from arq import Retry, cron
from arq.connections import RedisSettings
from sqlalchemy import select, update

from app.core.config import settings
from app.core.crypto import decrypt, encrypt, rotate
from app.core.db import SessionLocal, engine
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.models import Campaign, InstagramAccount, Organization
from app.models.base import AccountStatus, CampaignStatus
from app.services import retention
from app.services.campaigns import sync_campaign
from app.services.instagram import close_instagram_client, get_instagram_client
from app.services.instagram.base import InstagramAuthError, InstagramError
from app.services.webhooks import event_ids, handle_webhook_payload, is_transient

log = logging.getLogger("app.worker")


MAX_TRIES = 5
BACKOFF_SECONDS = (5, 15, 45, 120)  # entre as 5 tentativas


async def process_webhook(ctx: dict[str, Any], payload: dict[str, Any]) -> int:
    """Processa um webhook ja autenticado. Falhas temporarias repetem o job (arq.Retry) com
    backoff crescente; esgotadas as tentativas, loga so os ids dos eventos."""
    try:
        return await handle_webhook_payload(payload)
    except Exception as exc:
        if not is_transient(exc):
            raise
        tries = int(ctx.get("job_try", 1))
        if tries >= MAX_TRIES:
            log.error(
                "webhook descartado apos %d tentativas: %s",
                tries,
                ",".join(event_ids(payload)),
                extra={"event": "webhook_dropped"},
            )
            return 0
        delay = BACKOFF_SECONDS[min(tries - 1, len(BACKOFF_SECONDS) - 1)]
        log.warning("falha temporaria no webhook (tentativa %d): %s", tries, type(exc).__name__)
        raise Retry(defer=delay) from exc


async def poll_active_campaigns(ctx: dict[str, Any]) -> int:
    """Fallback por polling: lista os comentarios de cada campanha ativa."""
    threshold = datetime.now(UTC) - timedelta(seconds=settings.sync_interval_seconds)
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(Campaign.id, InstagramAccount.id)
                .join(Organization, Organization.id == Campaign.organization_id)
                .join(InstagramAccount, InstagramAccount.user_id == Organization.owner_id)
                .where(
                    Campaign.status == CampaignStatus.active.value,
                    Campaign.ig_media_id.is_not(None),
                    InstagramAccount.status == AccountStatus.active.value,
                    (Campaign.last_synced_at.is_(None)) | (Campaign.last_synced_at <= threshold),
                )
                .limit(200)
            )
        ).all()
    synced = 0
    for campaign_id, account_id in rows:
        async with SessionLocal() as db:
            try:
                campaign = await db.get(Campaign, campaign_id)
                account = await db.get(InstagramAccount, account_id)
                if campaign is None or account is None:
                    continue
                await sync_campaign(db, account, campaign)
                synced += 1
            except Exception:
                await db.rollback()
                log.exception("polling falhou", extra={"event": "poll"})
    return synced


async def end_expired_campaigns(ctx: dict[str, Any]) -> int:
    async with SessionLocal() as db:
        res = await db.execute(
            update(Campaign)
            .where(
                Campaign.status == CampaignStatus.active.value,
                Campaign.ends_at.is_not(None),
                Campaign.ends_at < datetime.now(UTC),
            )
            .values(status=CampaignStatus.ended.value, ended_at=Campaign.ends_at)
        )
        await db.commit()
        return res.rowcount or 0


async def refresh_tokens(ctx: dict[str, Any]) -> int:
    """Renova tokens que expiram em menos de 10 dias."""
    limit = datetime.now(UTC) + timedelta(days=10)
    refreshed = 0
    async with SessionLocal() as db:
        accounts = (
            (
                await db.execute(
                    select(InstagramAccount).where(
                        InstagramAccount.status == AccountStatus.active.value,
                        InstagramAccount.token_expires_at.is_not(None),
                        InstagramAccount.token_expires_at < limit,
                    )
                )
            )
            .scalars()
            .all()
        )
        for account in accounts:
            try:
                new = await get_instagram_client().refresh_token(decrypt(account.access_token_enc))
                account.access_token_enc = encrypt(new.access_token)
                account.token_expires_at = new.expires_at
                refreshed += 1
            except InstagramAuthError:
                account.status = AccountStatus.expired.value
            except (InstagramError, ValueError):
                log.warning("refresh de token falhou", extra={"event": "token_refresh"})
            await db.commit()
    return refreshed


async def retry_webhook_subscriptions(ctx: dict[str, Any]) -> int:
    """Refaz a assinatura de webhooks (subscribed_apps) que falhou na conexao."""
    done = 0
    async with SessionLocal() as db:
        accounts = (
            (
                await db.execute(
                    select(InstagramAccount).where(
                        InstagramAccount.status == AccountStatus.active.value,
                        InstagramAccount.webhook_subscribed.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        for account in accounts:
            try:
                ok = await get_instagram_client().subscribe_webhooks(
                    decrypt(account.access_token_enc), account.ig_user_id
                )
                if ok:
                    account.webhook_subscribed = True
                    done += 1
            except InstagramAuthError:
                account.status = AccountStatus.expired.value
            except (InstagramError, ValueError):
                log.warning("assinatura de webhook falhou", extra={"event": "subscribe"})
            await db.commit()
    return done


async def rotate_encrypted_tokens(ctx: dict[str, Any]) -> int:
    """Recifra os tokens do Instagram com a TOKEN_ENCRYPTION_KEY atual. So roda quando ha
    chave anterior configurada (rotacao em andamento)."""
    if not settings.token_encryption_key_previous.strip():
        return 0
    done = 0
    async with SessionLocal() as db:
        accounts = (await db.execute(select(InstagramAccount))).scalars().all()
        for account in accounts:
            try:
                new = rotate(account.access_token_enc)
            except ValueError:
                log.warning("token ilegivel na rotacao", extra={"event": "rotate"})
                continue
            if new != account.access_token_enc:
                account.access_token_enc = new
                done += 1
        await db.commit()
    log.info("tokens recifrados: %d", done, extra={"event": "rotate"})
    return done


async def apply_retention(ctx: dict[str, Any]) -> int:
    """Politica de retencao diaria (ver app/services/retention.py)."""
    async with SessionLocal() as db:
        res = await retention.purge(db)
    return res.interactions_anonymized


async def startup(ctx: dict[str, Any]) -> None:
    setup_logging()


async def shutdown(ctx: dict[str, Any]) -> None:
    await close_instagram_client()
    await close_redis()
    await engine.dispose()


class WorkerSettings:
    functions = [process_webhook]
    cron_jobs = [
        cron(poll_active_campaigns, second=0, run_at_startup=False, timeout=300),
        cron(end_expired_campaigns, second=30, run_at_startup=True),
        cron(refresh_tokens, minute=7, second=0, run_at_startup=True),
        cron(retry_webhook_subscriptions, minute={3, 13, 23, 33, 43, 53}, second=15),
        cron(rotate_encrypted_tokens, hour=4, minute=17, second=0, run_at_startup=True),
        cron(apply_retention, hour=5, minute=11, second=0, timeout=600),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_tries = MAX_TRIES
    job_timeout = 120
    keep_result = 60
