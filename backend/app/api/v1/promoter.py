import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, Pager, Promoter, promoter_membership
from app.core.errors import AppError, not_found
from app.core.rate_limit import check_rate_limit, client_ip
from app.models import (
    Campaign,
    InstagramAccount,
    Interaction,
    Membership,
    Organization,
    PointTransaction,
    PromoterProfile,
    Redemption,
    Reward,
)
from app.schemas.common import Page
from app.schemas.models import (
    ClaimIn,
    JoinIn,
    LeaderboardEntryOut,
    MembershipListOut,
    MembershipOut,
    MyRankOut,
    OrganizationPreviewOut,
    ProfilePatchIn,
    PromoterCampaignDetailOut,
    PromoterCampaignOut,
    PromoterHomeOut,
    PromoterLeaderboardOut,
    PromoterMyOut,
    PromoterRewardOut,
    RedeemIn,
    RedemptionOut,
    TransactionOut,
    UserEnvelope,
    VerificationOut,
)
from app.services import leaderboard as lb
from app.services import rewards as rewards_svc
from app.services import verification
from app.services.notifications import notify
from app.services.views import (
    interaction_out,
    interaction_query,
    load_redemption,
    membership_out,
    membership_preview_query,
    redeemed_counts,
    redemption_out,
    redemption_query,
    user_out,
)

router = APIRouter(tags=["promoter"])
public_router = APIRouter(tags=["promoter"])


# ------------------------------------------------------------------ convite / equipes


@public_router.get("/orgs/invite/{code}", response_model=OrganizationPreviewOut)
async def invite_preview(code: str, request: Request, db: DB):
    await check_rate_limit("invite", f"ip:{client_ip(request)}")
    m2 = Membership.__table__.alias("mc")
    count = (
        select(func.count())
        .select_from(m2)
        .where(m2.c.organization_id == Organization.id, m2.c.status == "approved")
        .correlate(Organization)
        .scalar_subquery()
    )
    res = (
        await db.execute(
            select(
                Organization,
                InstagramAccount.username,
                InstagramAccount.profile_picture_url,
                count,
            )
            .outerjoin(InstagramAccount, InstagramAccount.user_id == Organization.owner_id)
            .where(Organization.invite_code == code.strip().upper()[:16])
        )
    ).first()
    if res is None:
        raise AppError(404, "invalid_invite", "Código de convite inválido.")
    org, username, picture, n = res
    return OrganizationPreviewOut(
        id=org.id,
        name=org.name,
        instagram_username=username,
        instagram_profile_picture_url=picture,
        promoters_count=n or 0,
    )


@router.get("/promoter/memberships", response_model=MembershipListOut)
async def my_memberships(user: Promoter, db: DB):
    rows = await db.execute(
        membership_preview_query(Membership.promoter_id == user.id).order_by(
            Membership.joined_at.desc()
        )
    )
    return MembershipListOut(items=[membership_out(r) for r in rows])


@router.post("/promoter/memberships", status_code=201, response_model=MembershipOut)
async def join_team(body: JoinIn, request: Request, user: Promoter, db: DB):
    await check_rate_limit("invite", f"ip:{client_ip(request)}")
    org = (
        await db.execute(
            select(Organization).where(Organization.invite_code == body.invite_code.upper())
        )
    ).scalar_one_or_none()
    if org is None:
        raise AppError(400, "invalid_invite", "Código de convite inválido.")
    existing = (
        await db.execute(
            select(Membership)
            .where(Membership.organization_id == org.id, Membership.promoter_id == user.id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    approved = org.auto_approve_promoters
    now = datetime.now(UTC)
    if existing is not None:
        if existing.status in ("pending", "approved"):
            raise AppError(409, "already_member", "Você já faz parte desta equipe.")
        existing.status = "approved" if approved else "pending"
        existing.approved_at = now if approved else None
        existing.joined_at = now
        existing.approved_by = None
        membership = existing
    else:
        membership = Membership(
            organization_id=org.id,
            promoter_id=user.id,
            status="approved" if approved else "pending",
            approved_at=now if approved else None,
        )
        try:
            async with db.begin_nested():
                db.add(membership)
                await db.flush()
        except IntegrityError:
            raise AppError(409, "already_member", "Você já faz parte desta equipe.") from None
    profile = await db.get(PromoterProfile, user.id)
    handle = f" (@{profile.instagram_username})" if profile else ""
    await notify(
        db,
        org.owner_id,
        "join_request",
        "Novo promoter na equipe" if approved else "Novo pedido para entrar na equipe",
        f"{user.name}{handle} "
        + ("entrou na equipe." if approved else "quer entrar na sua equipe."),
        "/gestor/equipe",
    )
    # Auto-aprovacao NUNCA re-casa retroativamente: so ganha por eventos posteriores a entrada.
    await db.commit()
    row = (await db.execute(membership_preview_query(Membership.id == membership.id))).one()
    return membership_out(row)


@router.delete("/promoter/memberships/{membership_id}", status_code=204)
async def leave_team(membership_id: uuid.UUID, user: Promoter, db: DB):
    m = (
        await db.execute(
            select(Membership).where(
                Membership.id == membership_id, Membership.promoter_id == user.id
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found()
    m.status = "removed"
    await db.commit()
    return Response(status_code=204)


@router.patch("/promoter/profile", response_model=UserEnvelope)
async def patch_profile(body: ProfilePatchIn, user: Promoter, db: DB):
    profile = await db.get(PromoterProfile, user.id)
    if profile is None:
        raise not_found()
    if body.instagram_username != profile.instagram_username:
        taken = await db.scalar(
            select(PromoterProfile.user_id).where(
                PromoterProfile.instagram_username == body.instagram_username
            )
        )
        if taken is not None:
            raise AppError(
                409, "instagram_username_taken", "Este @ do Instagram já está cadastrado."
            )
        old = profile.instagram_username or "(sem @)"
        await verification.cancel_claims(db, user.id)
        profile.instagram_username = body.instagram_username
        profile.verified = False
        profile.verified_at = None
        profile.verification_method = None
        profile.ig_scoped_id = None
        # O gestor e o portao de identidade: trocar o @ volta toda aprovacao para pendente
        # (saldo e historico intactos) e NAO re-casa nada ate nova aprovacao manual.
        rows = (
            await db.execute(
                select(Membership, Organization.owner_id, Organization.name)
                .join(Organization, Organization.id == Membership.organization_id)
                .where(Membership.promoter_id == user.id, Membership.status == "approved")
                .with_for_update(of=Membership)
            )
        ).all()
        for m, owner_id, _org_name in rows:
            m.status = "pending"
            m.approved_at = None
            m.approved_by = None
            await notify(
                db,
                owner_id,
                "username_changed",
                "Promoter alterou o @ e precisa de nova aprovação",
                f"{user.name} alterou o @ de {old} para {body.instagram_username} "
                "e precisa de nova aprovação.",
                "/gestor/equipe",
            )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise AppError(
                409, "instagram_username_taken", "Este @ do Instagram já está cadastrado."
            ) from None
    return UserEnvelope(user=await user_out(db, user))


# ------------------------------------------------------------------ verificacao do @


async def _verification_out(db, user) -> VerificationOut:
    profile = await db.get(PromoterProfile, user.id)
    claim = await verification.pending_claim(db, user.id)
    return VerificationOut(
        instagram_username=profile.instagram_username if profile else None,
        verified=bool(profile and profile.verified),
        claim_username=claim.instagram_username if claim else None,
        code=claim.code if claim else None,
        expires_at=claim.expires_at if claim else None,
    )


@router.get("/promoter/verification", response_model=VerificationOut)
async def get_verification(user: Promoter, db: DB):
    return await _verification_out(db, user)


@router.post("/promoter/verification", response_model=VerificationOut)
async def start_verification(user: Promoter, db: DB):
    """Gera o codigo para verificar o PROPRIO @ (comentar em qualquer post de uma conta
    conectada ao app)."""
    await check_rate_limit("invite", f"user:{user.id}")
    profile = await db.get(PromoterProfile, user.id)
    if profile is None or not profile.instagram_username:
        raise AppError(400, "no_username", "Cadastre seu @ do Instagram primeiro.")
    await verification.start_claim(db, user.id, profile.instagram_username)
    await db.commit()
    return await _verification_out(db, user)


@router.post("/promoter/username-claims", response_model=VerificationOut)
async def claim_username(body: ClaimIn, user: Promoter, db: DB):
    """Disputa: pede um @ que outra pessoa cadastrou sem verificar. O @ so muda de dono
    quando o codigo chega num comentario feito por esse @."""
    await check_rate_limit("invite", f"user:{user.id}")
    await verification.start_claim(db, user.id, body.instagram_username)
    await db.commit()
    return await _verification_out(db, user)


# ------------------------------------------------------------------ campanhas


def _my_map(rows) -> dict[uuid.UUID, PromoterMyOut]:
    return {
        cid: PromoterMyOut(comment_done=c > 0, story_mentions_done=s, points_earned=int(p))
        for cid, c, s, p in rows
    }


async def _my_stats(db, membership_ids, campaign_ids):
    if not campaign_ids:
        return {}
    awarded = Interaction.status == "awarded"
    res = await db.execute(
        select(
            Interaction.campaign_id,
            func.count().filter(Interaction.type == "comment"),
            func.count().filter(Interaction.type == "story_mention"),
            func.coalesce(func.sum(Interaction.points_awarded), 0),
        )
        .where(
            Interaction.membership_id.in_(membership_ids),
            Interaction.campaign_id.in_(campaign_ids),
            awarded,
        )
        .group_by(Interaction.campaign_id)
    )
    return _my_map(res.all())


_EMPTY_MY = PromoterMyOut(comment_done=False, story_mentions_done=0, points_earned=0)


def _campaign_out(c: Campaign, my: PromoterMyOut | None) -> PromoterCampaignOut:
    return PromoterCampaignOut(
        id=c.id,
        organization_id=c.organization_id,
        title=c.title,
        description=c.description,
        instructions=c.instructions,
        status=c.status,
        permalink=c.permalink,
        media_type=c.media_type,
        media_url=c.media_url,
        thumbnail_url=c.thumbnail_url,
        caption=c.caption,
        starts_at=c.starts_at,
        ends_at=c.ends_at,
        points_comment=c.points_comment,
        points_story_mention=c.points_story_mention,
        max_story_mentions=c.max_story_mentions,
        my=my or _EMPTY_MY,
    )


@router.get("/promoter/campaigns", response_model=Page[PromoterCampaignOut])
async def my_campaigns(
    user: Promoter,
    db: DB,
    page: Pager,
    org_id: uuid.UUID | None = None,
    status: Literal["active", "ended"] | None = None,
):
    if org_id is not None:
        await promoter_membership(db, user, org_id)
    where = [
        Membership.promoter_id == user.id,
        Membership.status == "approved",
        Campaign.status.in_(["active", "ended"]),
    ]
    if org_id is not None:
        where.append(Campaign.organization_id == org_id)
    if status:
        where.append(Campaign.status == status)
    base = (
        select(Campaign)
        .join(Membership, Membership.organization_id == Campaign.organization_id)
        .where(*where)
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rows = (
        (
            await db.execute(
                base.order_by(Campaign.dispatched_at.desc().nulls_last(), Campaign.id)
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    mids = list(
        (
            await db.execute(
                select(Membership.id).where(
                    Membership.promoter_id == user.id, Membership.status == "approved"
                )
            )
        ).scalars()
    )
    my = await _my_stats(db, mids, [c.id for c in rows])
    return Page[PromoterCampaignOut](
        items=[_campaign_out(c, my.get(c.id)) for c in rows], total=total or 0
    )


@router.get("/promoter/campaigns/{campaign_id}", response_model=PromoterCampaignDetailOut)
async def my_campaign(campaign_id: uuid.UUID, user: Promoter, db: DB):
    row = (
        await db.execute(
            select(Campaign, Membership)
            .join(
                Membership,
                (Membership.organization_id == Campaign.organization_id)
                & (Membership.promoter_id == user.id)
                & (Membership.status == "approved"),
            )
            .where(Campaign.id == campaign_id, Campaign.status != "draft")
        )
    ).first()
    if row is None:
        raise not_found()
    campaign, membership = row
    my = (await _my_stats(db, [membership.id], [campaign.id])).get(campaign.id)
    inter = await db.execute(
        interaction_query()
        .where(Interaction.campaign_id == campaign.id, Interaction.membership_id == membership.id)
        .order_by(Interaction.occurred_at.desc())
        .limit(50)
    )
    base = _campaign_out(campaign, my)
    return PromoterCampaignDetailOut(
        **base.model_dump(), my_interactions=[interaction_out(r) for r in inter]
    )


# ------------------------------------------------------------------ home / ranking


@router.get("/promoter/home", response_model=PromoterHomeOut)
async def home(user: Promoter, db: DB, org_id: uuid.UUID | None = None):
    m = await promoter_membership(db, user, org_id)
    mem_row = (await db.execute(membership_preview_query(Membership.id == m.id))).one()
    mem = membership_out(mem_row)
    rank, _points = await lb.rank_of(db, m.organization_id, "all", m.id)
    campaigns = (
        (
            await db.execute(
                select(Campaign)
                .where(Campaign.organization_id == m.organization_id, Campaign.status == "active")
                .order_by(Campaign.dispatched_at.desc().nulls_last())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    my = await _my_stats(db, [m.id], [c.id for c in campaigns])
    txs = (
        (
            await db.execute(
                select(PointTransaction)
                .where(PointTransaction.membership_id == m.id)
                .order_by(PointTransaction.created_at.desc(), PointTransaction.id)
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    affordable = await db.scalar(
        select(func.count())
        .select_from(Reward)
        .where(
            Reward.organization_id == m.organization_id,
            Reward.is_active.is_(True),
            Reward.archived_at.is_(None),
            Reward.cost_points <= m.points_balance,
            or_(Reward.stock.is_(None), Reward.stock > 0),
        )
    )
    return PromoterHomeOut(
        membership=mem,
        rank=rank,
        promoters_count=mem.organization.promoters_count,
        active_campaigns=[_campaign_out(c, my.get(c.id)) for c in campaigns],
        recent_transactions=[TransactionOut.model_validate(t) for t in txs],
        affordable_rewards_count=affordable or 0,
    )


@router.get("/promoter/leaderboard", response_model=PromoterLeaderboardOut)
async def my_leaderboard(
    user: Promoter,
    db: DB,
    org_id: uuid.UUID | None = None,
    period: Literal["all", "30d", "7d"] = "all",
    limit: int = Query(20, ge=1, le=100),
):
    m = await promoter_membership(db, user, org_id)
    entries = await lb.top_entries(db, m.organization_id, period, limit)
    rank, points = await lb.rank_of(db, m.organization_id, period, m.id)
    return PromoterLeaderboardOut(
        items=[
            LeaderboardEntryOut(
                rank=e.rank,
                membership_id=e.membership_id,
                name=e.name,
                instagram_username=e.instagram_username,
                points=e.points,
            )
            for e in entries
        ],
        me=MyRankOut(rank=rank, points=points),
    )


# ------------------------------------------------------------------ lojinha


@router.get("/promoter/rewards", response_model=Page[PromoterRewardOut])
async def my_rewards(user: Promoter, db: DB, page: Pager, org_id: uuid.UUID | None = None):
    m = await promoter_membership(db, user, org_id)
    where = [
        Reward.organization_id == m.organization_id,
        Reward.is_active.is_(True),
        Reward.archived_at.is_(None),
    ]
    total = await db.scalar(select(func.count()).select_from(Reward).where(*where))
    rows = (
        (
            await db.execute(
                select(Reward)
                .where(*where)
                .order_by(Reward.cost_points, Reward.id)
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    ids = [r.id for r in rows]
    counts = await redeemed_counts(db, ids)
    mine: dict[uuid.UUID, int] = {}
    if ids:
        res = await db.execute(
            select(Redemption.reward_id, func.count())
            .where(
                Redemption.membership_id == m.id,
                Redemption.reward_id.in_(ids),
                Redemption.status != "cancelled",
            )
            .group_by(Redemption.reward_id)
        )
        mine = dict(res.all())
    items = []
    for r in rows:
        n = mine.get(r.id, 0)
        in_stock = r.stock is None or r.stock > 0
        under_limit = r.max_per_promoter is None or n < r.max_per_promoter
        items.append(
            PromoterRewardOut(
                id=r.id,
                name=r.name,
                description=r.description,
                image_url=r.image_url,
                cost_points=r.cost_points,
                stock=r.stock,
                max_per_promoter=r.max_per_promoter,
                is_active=r.is_active,
                redeemed_count=counts.get(r.id, 0),
                created_at=r.created_at,
                can_afford=m.points_balance >= r.cost_points,
                my_redemptions_count=n,
                available=in_stock and under_limit,
            )
        )
    return Page[PromoterRewardOut](items=items, total=total or 0)


@router.post("/promoter/rewards/{reward_id}/redeem", status_code=201, response_model=RedemptionOut)
async def redeem(reward_id: uuid.UUID, body: RedeemIn, user: Promoter, db: DB):
    await check_rate_limit("redeem", f"user:{user.id}")
    org_id = await db.scalar(select(Reward.organization_id).where(Reward.id == reward_id))
    if org_id is None:
        raise not_found("Recompensa não encontrada.")
    membership_id = await db.scalar(
        select(Membership.id).where(
            Membership.organization_id == org_id, Membership.promoter_id == user.id
        )
    )
    if membership_id is None:
        raise not_found("Recompensa não encontrada.")
    redemption = await rewards_svc.redeem(db, membership_id, reward_id, body.request_id)
    return await load_redemption(db, redemption.id, manager_view=False)


@router.get("/promoter/redemptions", response_model=Page[RedemptionOut])
async def my_redemptions(user: Promoter, db: DB, page: Pager, org_id: uuid.UUID | None = None):
    if org_id is not None:
        await promoter_membership(db, user, org_id)
    mids = select(Membership.id).where(
        Membership.promoter_id == user.id, Membership.status == "approved"
    )
    if org_id is not None:
        mids = mids.where(Membership.organization_id == org_id)
    where = Redemption.membership_id.in_(mids)
    total = await db.scalar(select(func.count()).select_from(Redemption).where(where))
    rows = await db.execute(
        redemption_query()
        .where(where)
        .order_by(Redemption.created_at.desc(), Redemption.id)
        .limit(page.limit)
        .offset(page.offset)
    )
    return Page[RedemptionOut](
        items=[redemption_out(r, manager_view=False) for r in rows], total=total or 0
    )


@router.get("/promoter/transactions", response_model=Page[TransactionOut])
async def my_transactions(user: Promoter, db: DB, page: Pager, org_id: uuid.UUID | None = None):
    if org_id is not None:
        await promoter_membership(db, user, org_id)
    mids = select(Membership.id).where(
        Membership.promoter_id == user.id, Membership.status == "approved"
    )
    if org_id is not None:
        mids = mids.where(Membership.organization_id == org_id)
    where = PointTransaction.membership_id.in_(mids)
    total = await db.scalar(select(func.count()).select_from(PointTransaction).where(where))
    rows = (
        (
            await db.execute(
                select(PointTransaction)
                .where(where)
                .order_by(PointTransaction.created_at.desc(), PointTransaction.id)
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    return Page[TransactionOut](
        items=[TransactionOut.model_validate(t) for t in rows], total=total or 0
    )
