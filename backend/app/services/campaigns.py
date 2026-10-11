import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, not_found
from app.core.redis import get_redis
from app.models import Campaign, InstagramAccount, Interaction, Membership, Organization
from app.models.base import CampaignSource, CampaignStatus, InteractionStatus, InteractionType
from app.services.instagram import call_with_account
from app.services.instagram.base import IGMedia
from app.services.interactions import InboundEvent, process_event
from app.services.notifications import notify_many

DUPLICATE_POST_MESSAGE = "Já existe uma campanha em andamento para este post."


async def get_org_campaign(
    db: AsyncSession, org_id: uuid.UUID, campaign_id: uuid.UUID, *, lock: bool = False
) -> Campaign:
    stmt = select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if campaign is None:
        raise not_found()
    return campaign


async def get_account(db: AsyncSession, user_id: uuid.UUID) -> InstagramAccount | None:
    res = await db.execute(select(InstagramAccount).where(InstagramAccount.user_id == user_id))
    return res.scalar_one_or_none()


async def require_account(db: AsyncSession, org: Organization) -> InstagramAccount:
    account = await get_account(db, org.owner_id)
    if account is None:
        raise AppError(
            400, "instagram_not_connected", "Conecte sua conta do Instagram para continuar."
        )
    return account


# ------------------------------------------------------------------ estatisticas


@dataclass
class Stats:
    comments_awarded: int = 0
    story_mentions_awarded: int = 0
    participants: int = 0
    points_issued: int = 0
    unmatched: int = 0


async def campaign_stats(db: AsyncSession, campaign_ids: list[uuid.UUID]) -> dict[uuid.UUID, Stats]:
    """Estatisticas de varias campanhas em UMA consulta agrupada."""
    if not campaign_ids:
        return {}
    awarded = Interaction.status == InteractionStatus.awarded.value
    res = await db.execute(
        select(
            Interaction.campaign_id,
            func.count().filter(awarded, Interaction.type == InteractionType.comment.value),
            func.count().filter(awarded, Interaction.type == InteractionType.story_mention.value),
            func.count(func.distinct(Interaction.membership_id)).filter(awarded),
            func.coalesce(func.sum(Interaction.points_awarded).filter(awarded), 0),
            func.count().filter(Interaction.status == InteractionStatus.unmatched.value),
        )
        .where(Interaction.campaign_id.in_(campaign_ids))
        .group_by(Interaction.campaign_id)
    )
    out: dict[uuid.UUID, Stats] = {}
    for cid, c, s, p, pts, un in res.all():
        out[cid] = Stats(c, s, p, int(pts), un)
    return out


# ------------------------------------------------------------------ criacao


def _apply_media(campaign: Campaign, media: IGMedia) -> None:
    campaign.ig_media_id = media.id
    campaign.permalink = media.permalink
    campaign.media_type = media.media_type
    campaign.media_url = media.media_url
    campaign.thumbnail_url = media.thumbnail_url
    campaign.caption = media.caption


async def create_campaign(db: AsyncSession, org: Organization, data: dict) -> Campaign:
    """Cria a campanha em rascunho (sem commit). `data` ja validado."""
    account = await require_account(db, org)
    campaign = Campaign(
        organization_id=org.id,
        title=data["title"],
        description=data.get("description"),
        instructions=data.get("instructions"),
        status=CampaignStatus.draft.value,
        source=data["source"],
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
        points_comment=data["points_comment"],
        points_story_mention=data["points_story_mention"],
        max_story_mentions=data["max_story_mentions"],
    )
    if data["source"] == CampaignSource.existing.value:
        media_id = data["ig_media_id"]
        dup = await db.scalar(
            select(Campaign.id).where(
                Campaign.organization_id == org.id,
                Campaign.ig_media_id == media_id,
                Campaign.status != CampaignStatus.ended.value,
            )
        )
        if dup is not None:
            raise AppError(409, "conflict", DUPLICATE_POST_MESSAGE)
        media = await call_with_account(
            db, account, lambda c, tok: c.get_media(tok, account.ig_user_id, media_id)
        )
        _apply_media(campaign, media)
    else:
        campaign.publish_image_url = data["image_url"]
        campaign.caption = data["caption"]
        campaign.media_url = data["image_url"]
        campaign.media_type = "IMAGE"
    try:
        async with db.begin_nested():
            db.add(campaign)
            await db.flush()
    except IntegrityError:
        # indice unico parcial (organization_id, ig_media_id) onde status <> ended
        raise AppError(409, "conflict", DUPLICATE_POST_MESSAGE) from None
    return campaign


def _validate_window(campaign: Campaign, now: datetime) -> None:
    """Revalida a janela com o inicio efetivo (starts_at ou o momento do envio)."""
    start = campaign.starts_at or now
    if campaign.ends_at is not None and (campaign.ends_at <= start or campaign.ends_at <= now):
        msg = "O término da campanha já passou ou é anterior ao início. Ajuste a data de término."
        raise AppError(400, "validation_error", msg, {"ends_at": msg})


async def _poll_container(db: AsyncSession, account: InstagramAccount, container_id: str) -> str:
    status = "IN_PROGRESS"
    for attempt in range(10):
        status = await call_with_account(
            db, account, lambda c, tok: c.get_container_status(tok, container_id)
        )
        if status != "IN_PROGRESS":
            return status
        if attempt < 9:
            await asyncio.sleep(1.5)
    return status


async def _publish(
    db: AsyncSession, org: Organization, account: InstagramAccount, campaign_id: uuid.UUID
) -> None:
    """Publicacao idempotente: o id do container e persistido ANTES de media_publish; repetir
    o envio reconcilia pelo status do container em vez de publicar de novo."""
    redis = get_redis()
    lock_key = f"publish-lock:{campaign_id}"
    if not await redis.set(lock_key, "1", nx=True, ex=180):
        raise AppError(409, "conflict", "A publicação desta campanha já está em andamento.")
    try:
        c = await get_org_campaign(db, org.id, campaign_id, lock=True)
        if c.ig_media_id or c.status != CampaignStatus.draft.value:
            await db.commit()
            return
        image_url = c.publish_image_url or ""
        caption = c.caption or ""
        if c.publish_container_id is None:
            new_container = await call_with_account(
                db,
                account,
                lambda cl, tok: cl.create_media_container(
                    tok, account.ig_user_id, image_url, caption
                ),
            )
            c.publish_container_id = new_container
            c.publish_container_at = datetime.now(UTC)
        await db.commit()  # container persistido antes de qualquer publish
        container_id = c.publish_container_id or ""
        since = (c.publish_container_at or datetime.now(UTC)) - timedelta(minutes=2)

        status = await _poll_container(db, account, container_id)
        if status == "PUBLISHED":  # resposta do publish anterior se perdeu
            media_id = await call_with_account(
                db,
                account,
                lambda cl, tok: cl.find_published_media(tok, account.ig_user_id, caption, since),
            )
            if media_id is None:
                raise AppError(
                    502,
                    "instagram_error",
                    "O post já foi publicado no Instagram, mas ainda não conseguimos localizá-lo. "
                    "Tente novamente em instantes.",
                )
        elif status == "FINISHED":
            media_id = await call_with_account(
                db,
                account,
                lambda cl, tok: cl.publish_container(tok, account.ig_user_id, container_id),
            )
        elif status in ("ERROR", "EXPIRED"):
            c = await get_org_campaign(db, org.id, campaign_id, lock=True)
            c.publish_container_id = None  # container morto: a proxima tentativa cria outro
            c.publish_container_at = None
            await db.commit()
            raise AppError(
                502,
                "instagram_error",
                "O Instagram recusou a imagem. Use um JPEG público e válido.",
            )
        else:
            raise AppError(
                502,
                "instagram_error",
                "O Instagram ainda está processando a imagem. Tente novamente em instantes.",
            )

        c = await get_org_campaign(db, org.id, campaign_id, lock=True)
        c.ig_media_id = media_id
        try:
            media = await call_with_account(
                db, account, lambda cl, tok: cl.get_media(tok, account.ig_user_id, media_id)
            )
            _apply_media(c, media)
            c.media_url = media.media_url or image_url
        except AppError:
            pass  # publicado; os detalhes completam no proximo sync
        await db.commit()
        keys = await _media_cache_keys(account)
        await redis.delete(*keys)
    finally:
        await redis.delete(lock_key)


async def dispatch_campaign(
    db: AsyncSession, org: Organization, campaign_id: uuid.UUID
) -> Campaign:
    """Publica (se source=publish), ativa e notifica os promoters aprovados. Faz commit.

    A transicao rascunho -> ativa (e as notificacoes) acontece exatamente uma vez: o status e
    revalidado depois de reobter o lock.
    """
    campaign = await get_org_campaign(db, org.id, campaign_id, lock=True)
    if campaign.status != CampaignStatus.draft.value:
        raise AppError(400, "campaign_not_editable", "Esta campanha já foi enviada.")
    _validate_window(campaign, datetime.now(UTC))
    account = await require_account(db, org)
    if campaign.source == CampaignSource.publish.value and not campaign.ig_media_id:
        await db.commit()  # nao segura o lock durante chamadas externas
        await _publish(db, org, account, campaign_id)
        campaign = await get_org_campaign(db, org.id, campaign_id, lock=True)
        if campaign.status != CampaignStatus.draft.value:
            raise AppError(400, "campaign_not_editable", "Esta campanha já foi enviada.")
    now = datetime.now(UTC)
    _validate_window(campaign, now)
    campaign.status = CampaignStatus.active.value
    campaign.dispatched_at = now
    if campaign.starts_at is None:
        campaign.starts_at = now
    promoters = await db.execute(
        select(Membership.promoter_id).where(
            Membership.organization_id == org.id, Membership.status == "approved"
        )
    )
    await notify_many(
        db,
        list(promoters.scalars()),
        "campaign_dispatched",
        "Nova campanha disponível",
        f"{org.name} liberou a campanha “{campaign.title}”. Comente e ganhe pontos!",
        f"/promoter/campanhas/{campaign.id}",
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "conflict", DUPLICATE_POST_MESSAGE) from None
    return campaign


async def end_campaign(db: AsyncSession, org: Organization, campaign_id: uuid.UUID) -> Campaign:
    campaign = await get_org_campaign(db, org.id, campaign_id, lock=True)
    if campaign.status != CampaignStatus.active.value:
        raise AppError(400, "campaign_not_active", "A campanha não está ativa.")
    campaign.status = CampaignStatus.ended.value
    await db.commit()
    return campaign


# ------------------------------------------------------------------ sync (polling)


@dataclass
class SyncResult:
    fetched: int = 0
    new_interactions: int = 0
    awarded: int = 0


async def _known_comment_ids(db: AsyncSession, ids: list[str]) -> set[str]:
    if not ids:
        return set()
    res = await db.execute(
        select(Interaction.ig_event_id).where(
            Interaction.type == InteractionType.comment.value,
            Interaction.ig_event_id.in_(ids),
        )
    )
    return set(res.scalars())


async def _save_sync_progress(
    db: AsyncSession, campaign_id: uuid.UUID, cursor: str | None, *, full_pass: bool = False
) -> None:
    values: dict = {"sync_cursor": cursor, "last_synced_at": datetime.now(UTC)}
    if full_pass:
        values["sync_full_pass_at"] = datetime.now(UTC)
    await db.execute(update(Campaign).where(Campaign.id == campaign_id).values(**values))
    await db.commit()


async def sync_campaign(
    db: AsyncSession, account: InstagramAccount, campaign: Campaign
) -> SyncResult:
    """Lista os comentarios pagina a pagina e os entrega ao mesmo pipeline do webhook.

    Cada execucao tem um orcamento de paginas (SYNC_PAGES_PER_RUN). Se for cortada, o cursor
    de continuacao fica na campanha e a proxima execucao retoma dele; ao fim da listagem o
    cursor e limpo. Depois de uma passada completa, uma execucao que comeca do inicio pode
    parar ao achar uma pagina so com comentarios ja conhecidos (a API lista do mais novo).
    """
    media_id = campaign.ig_media_id
    if not media_id:
        raise AppError(400, "campaign_not_active", "A campanha ainda não tem post vinculado.")
    campaign_id = campaign.id
    cursor = campaign.sync_cursor
    early_stop_ok = campaign.sync_full_pass_at is not None and cursor is None
    result = SyncResult()
    epoch = datetime.fromtimestamp(0, UTC)
    pages = 0
    while True:
        page = await call_with_account(
            db,
            account,
            lambda c, tok, after=cursor: c.list_comments_page(
                tok, account.ig_user_id, media_id, after, settings.sync_page_size
            ),
        )
        pages += 1
        result.fetched += len(page.items)
        known = await _known_comment_ids(db, [c.id for c in page.items])
        fresh = [c for c in page.items if c.id not in known]
        for c in sorted(fresh, key=lambda x: x.timestamp or epoch):  # o mais antigo premia
            ev = InboundEvent(
                type=InteractionType.comment.value,
                ig_event_id=c.id,
                account_ig_id=account.ig_user_id,
                occurred_at=c.timestamp or datetime.now(UTC),
                from_id=c.from_id,
                from_username=c.username,
                media_id=media_id,
                text=c.text,
                parent_id=c.parent_id,
            )
            out = await process_event(db, ev)
            if out.outcome == "created":
                result.new_interactions += 1
                if out.interaction is not None and out.interaction.status == "awarded":
                    result.awarded += 1
        if not page.next_cursor:
            await _save_sync_progress(db, campaign_id, None, full_pass=True)
            break
        if early_stop_ok and not fresh:
            await _save_sync_progress(db, campaign_id, None)
            break
        cursor = page.next_cursor
        await _save_sync_progress(db, campaign_id, cursor)  # retomavel se a execucao cair
        if pages >= settings.sync_pages_per_run:
            break  # orcamento esgotado: continua da proxima execucao
    return result


# ------------------------------------------------------------------ cache de midia


async def _media_cache_keys(account: InstagramAccount) -> list[str]:
    return [k async for k in get_redis().scan_iter(f"igmedia:{account.id}:*")] or [
        f"igmedia:{account.id}:none"
    ]


async def list_media_cached(
    db: AsyncSession, account: InstagramAccount, after: str | None, limit: int
) -> dict:

    key = f"igmedia:{account.id}:{after or ''}:{limit}"
    r = get_redis()
    cached = await r.get(key)
    if cached:
        return json.loads(cached)
    page = await call_with_account(
        db, account, lambda c, tok: c.list_media(tok, account.ig_user_id, after, limit)
    )
    payload = {
        "items": [
            {
                "id": m.id,
                "caption": m.caption,
                "media_type": m.media_type,
                "media_product_type": m.media_product_type,
                "media_url": m.media_url,
                "thumbnail_url": m.thumbnail_url,
                "permalink": m.permalink,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "like_count": m.like_count,
                "comments_count": m.comments_count,
            }
            for m in page.items
        ],
        "next_cursor": page.next_cursor,
    }
    await r.set(key, json.dumps(payload), ex=settings.instagram_media_cache_seconds)
    return payload
