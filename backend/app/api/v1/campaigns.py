import uuid
from typing import Literal

from fastapi import APIRouter, Response
from sqlalchemy import func, select

from app.api.deps import DB, Manager, Pager
from app.core.errors import AppError
from app.core.rate_limit import check_rate_limit
from app.models import Campaign, Interaction
from app.models.base import CampaignSource, CampaignStatus
from app.schemas.common import Page
from app.schemas.models import (
    CampaignCreateIn,
    CampaignOut,
    CampaignPatchIn,
    CampaignStatsOut,
    InteractionOut,
    SyncOut,
)
from app.services import campaigns as svc
from app.services.views import interaction_out, interaction_query

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _out(c: Campaign, stats: svc.Stats | None) -> CampaignOut:
    s = stats or svc.Stats()
    return CampaignOut(
        id=c.id,
        title=c.title,
        description=c.description,
        instructions=c.instructions,
        status=c.status,
        source=c.source,
        ig_media_id=c.ig_media_id,
        permalink=c.permalink,
        media_type=c.media_type,
        media_url=c.media_url,
        thumbnail_url=c.thumbnail_url,
        caption=c.caption,
        publish_image_url=c.publish_image_url,
        starts_at=c.starts_at,
        ends_at=c.ends_at,
        points_comment=c.points_comment,
        points_story_mention=c.points_story_mention,
        max_story_mentions=c.max_story_mentions,
        dispatched_at=c.dispatched_at,
        last_synced_at=c.last_synced_at,
        created_at=c.created_at,
        stats=CampaignStatsOut(**s.__dict__),
    )


async def _single(db, campaign: Campaign) -> CampaignOut:
    stats = await svc.campaign_stats(db, [campaign.id])
    return _out(campaign, stats.get(campaign.id))


@router.get("", response_model=Page[CampaignOut])
async def list_campaigns(
    ctx: Manager,
    db: DB,
    page: Pager,
    status: Literal["draft", "active", "ended"] | None = None,
):
    where = [Campaign.organization_id == ctx.org.id]
    if status:
        where.append(Campaign.status == status)
    total = await db.scalar(select(func.count()).select_from(Campaign).where(*where))
    rows = (
        (
            await db.execute(
                select(Campaign)
                .where(*where)
                .order_by(Campaign.created_at.desc(), Campaign.id)
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    stats = await svc.campaign_stats(db, [c.id for c in rows])  # uma consulta agrupada
    return Page[CampaignOut](items=[_out(c, stats.get(c.id)) for c in rows], total=total or 0)


@router.post("", status_code=201, response_model=CampaignOut)
async def create_campaign(body: CampaignCreateIn, ctx: Manager, db: DB):
    fields: dict[str, str] = {}
    if body.source == CampaignSource.existing.value:
        if not body.ig_media_id:
            fields["ig_media_id"] = "Escolha um post do Instagram."
    else:
        if not body.image_url:
            fields["image_url"] = "Envie a imagem do post."
        if not body.caption or not body.caption.strip():
            fields["caption"] = "Escreva a legenda do post."
    if fields:
        raise AppError(422, "validation_error", "Dados inválidos.", fields)
    data = body.model_dump(exclude={"dispatch"})
    try:
        campaign = await svc.create_campaign(db, ctx.org, data)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    if body.dispatch:
        campaign = await svc.dispatch_campaign(db, ctx.org, campaign.id)
    return await _single(db, campaign)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: uuid.UUID, ctx: Manager, db: DB):
    campaign = await svc.get_org_campaign(db, ctx.org.id, campaign_id)
    return await _single(db, campaign)


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def patch_campaign(campaign_id: uuid.UUID, body: CampaignPatchIn, ctx: Manager, db: DB):
    campaign = await svc.get_org_campaign(db, ctx.org.id, campaign_id, lock=True)
    if campaign.status == CampaignStatus.ended.value:
        raise AppError(400, "campaign_not_editable", "Campanhas encerradas não podem ser editadas.")
    sent = body.model_fields_set
    locked = {"points_comment", "points_story_mention", "max_story_mentions"} & sent
    if locked and campaign.status != CampaignStatus.draft.value:
        raise AppError(
            400,
            "campaign_not_editable",
            "Os pontos só podem ser alterados enquanto a campanha é rascunho.",
        )
    if "title" in sent and body.title:
        campaign.title = body.title
    if "description" in sent:
        campaign.description = body.description
    if "instructions" in sent:
        campaign.instructions = body.instructions
    if "points_comment" in sent and body.points_comment is not None:
        campaign.points_comment = body.points_comment
    if "points_story_mention" in sent and body.points_story_mention is not None:
        campaign.points_story_mention = body.points_story_mention
    if "max_story_mentions" in sent and body.max_story_mentions is not None:
        campaign.max_story_mentions = body.max_story_mentions
    if campaign.points_comment == 0 and campaign.points_story_mention == 0:
        raise AppError(
            422,
            "validation_error",
            "Dados inválidos.",
            {"points_comment": "Defina pontos para ao menos uma ação."},
        )
    if "ends_at" in sent:
        if body.ends_at is not None and campaign.starts_at and body.ends_at <= campaign.starts_at:
            raise AppError(
                422,
                "validation_error",
                "Dados inválidos.",
                {"ends_at": "O término deve ser depois do início."},
            )
        campaign.ends_at = body.ends_at
    await db.commit()
    return await _single(db, campaign)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: uuid.UUID, ctx: Manager, db: DB):
    campaign = await svc.get_org_campaign(db, ctx.org.id, campaign_id, lock=True)
    if campaign.status != CampaignStatus.draft.value:
        raise AppError(400, "campaign_not_editable", "Só é possível excluir campanhas em rascunho.")
    await db.delete(campaign)
    await db.commit()
    return Response(status_code=204)


@router.post("/{campaign_id}/dispatch", response_model=CampaignOut)
async def dispatch(campaign_id: uuid.UUID, ctx: Manager, db: DB):
    campaign = await svc.dispatch_campaign(db, ctx.org, campaign_id)
    return await _single(db, campaign)


@router.post("/{campaign_id}/end", response_model=CampaignOut)
async def end(campaign_id: uuid.UUID, ctx: Manager, db: DB):
    campaign = await svc.end_campaign(db, ctx.org, campaign_id)
    return await _single(db, campaign)


@router.post("/{campaign_id}/sync", response_model=SyncOut)
async def sync(campaign_id: uuid.UUID, ctx: Manager, db: DB):
    await check_rate_limit("sync", f"user:{ctx.user.id}")
    campaign = await svc.get_org_campaign(db, ctx.org.id, campaign_id)
    if campaign.status != CampaignStatus.active.value:
        raise AppError(400, "campaign_not_active", "A campanha não está ativa.")
    account = await svc.require_account(db, ctx.org)
    result = await svc.sync_campaign(db, account, campaign)
    return SyncOut(
        fetched=result.fetched,
        new_interactions=result.new_interactions,
        awarded=result.awarded,
    )


@router.get("/{campaign_id}/interactions", response_model=Page[InteractionOut])
async def list_interactions(
    campaign_id: uuid.UUID,
    ctx: Manager,
    db: DB,
    page: Pager,
    type: Literal["comment", "story_mention"] | None = None,
    status: Literal["awarded", "duplicate", "unmatched", "out_of_window"] | None = None,
):
    campaign = await svc.get_org_campaign(db, ctx.org.id, campaign_id)
    where = [Interaction.campaign_id == campaign.id, Interaction.organization_id == ctx.org.id]
    if type:
        where.append(Interaction.type == type)
    if status:
        where.append(Interaction.status == status)
    total = await db.scalar(select(func.count()).select_from(Interaction).where(*where))
    rows = await db.execute(
        interaction_query()
        .where(*where)
        .order_by(Interaction.occurred_at.desc(), Interaction.id)
        .limit(page.limit)
        .offset(page.offset)
    )
    return Page[InteractionOut](items=[interaction_out(r) for r in rows], total=total or 0)
