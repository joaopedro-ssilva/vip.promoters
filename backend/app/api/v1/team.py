import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, Manager, Pager
from app.api.v1.auth import new_invite_code
from app.core.config import settings
from app.core.errors import AppError, not_found
from app.models import Membership, PromoterProfile, User
from app.schemas.common import Page
from app.schemas.models import (
    AdjustPointsIn,
    InviteOut,
    LeaderboardEntryOut,
    LeaderboardOut,
    MemberOut,
    MemberPromoterOut,
    OrganizationOut,
    OrganizationPatchIn,
)
from app.services import leaderboard as lb
from app.services.interactions import rematch_membership
from app.services.notifications import notify
from app.services.points import adjust_points
from app.services.views import organization_out

router = APIRouter(tags=["team"])


def _member_out(m: Membership, u: User, p: PromoterProfile | None) -> MemberOut:
    return MemberOut(
        id=m.id,
        status=m.status,
        points_balance=m.points_balance,
        total_earned=m.total_earned,
        joined_at=m.joined_at,
        approved_at=m.approved_at,
        promoter=MemberPromoterOut(
            id=u.id,
            name=u.name,
            email=u.email,
            instagram_username=p.instagram_username if p else None,
            verified=p.verified if p else False,
        ),
    )


def _member_stmt(org_id: uuid.UUID):
    return (
        select(Membership, User, PromoterProfile)
        .join(User, User.id == Membership.promoter_id)
        .outerjoin(PromoterProfile, PromoterProfile.user_id == Membership.promoter_id)
        .where(Membership.organization_id == org_id)
    )


async def _get_member(db, org_id: uuid.UUID, member_id: uuid.UUID) -> MemberOut:
    row = (await db.execute(_member_stmt(org_id).where(Membership.id == member_id))).first()
    if row is None:
        raise not_found()
    return _member_out(*row)


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.patch("/organization", response_model=OrganizationOut)
async def patch_organization(body: OrganizationPatchIn, ctx: Manager, db: DB):
    if body.name is not None:
        ctx.org.name = body.name
    if body.auto_approve_promoters is not None:
        ctx.org.auto_approve_promoters = body.auto_approve_promoters
    await db.commit()
    return await organization_out(db, ctx.org)


def _invite(code: str) -> InviteOut:
    return InviteOut(invite_code=code, invite_url=f"{settings.app_base_url}/convite/{code}")


@router.get("/team/invite", response_model=InviteOut)
async def get_invite(ctx: Manager):
    return _invite(ctx.org.invite_code)


@router.post("/team/invite/rotate", response_model=InviteOut)
async def rotate_invite(ctx: Manager, db: DB):
    for _ in range(5):
        code = new_invite_code()
        try:
            async with db.begin_nested():
                ctx.org.invite_code = code
                await db.flush()
            break
        except IntegrityError:
            continue
    await db.commit()
    return _invite(ctx.org.invite_code)


@router.get("/team/members", response_model=Page[MemberOut])
async def list_members(
    ctx: Manager,
    db: DB,
    page: Pager,
    status: Literal["pending", "approved", "rejected", "removed"] | None = None,
    search: str | None = Query(None, max_length=100),
):
    stmt = _member_stmt(ctx.org.id)
    if status:
        stmt = stmt.where(Membership.status == status)
    if search and search.strip():
        like = _like(search.strip().lstrip("@"))
        stmt = stmt.where(
            or_(
                User.name.ilike(like, escape="\\"),
                User.email.ilike(like, escape="\\"),
                PromoterProfile.instagram_username.ilike(like, escape="\\"),
            )
        )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await db.execute(
        stmt.order_by(Membership.joined_at.desc(), Membership.id)
        .limit(page.limit)
        .offset(page.offset)
    )
    return Page[MemberOut](items=[_member_out(*r) for r in rows], total=total or 0)


async def _load_for_update(db, org_id: uuid.UUID, member_id: uuid.UUID) -> Membership:
    m = (
        await db.execute(
            select(Membership)
            .where(Membership.id == member_id, Membership.organization_id == org_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if m is None:
        raise not_found()
    return m


@router.post("/team/members/{member_id}/approve", response_model=MemberOut)
async def approve_member(member_id: uuid.UUID, ctx: Manager, db: DB):
    m = await _load_for_update(db, ctx.org.id, member_id)
    newly = m.status != "approved" or m.approved_by is None
    was_approved = m.status == "approved"
    if newly:
        m.status = "approved"
        m.approved_by = ctx.user.id  # aprovacao manual: prova de identidade do @
        m.approved_at = datetime.now(UTC)
    if newly and not was_approved:
        await notify(
            db,
            m.promoter_id,
            "membership_approved",
            "Você foi aprovado!",
            f"{ctx.org.name} aprovou você na equipe. Já dá para participar das campanhas.",
            "/promoter",
        )
    await db.commit()
    if newly:
        await rematch_membership(db, m.id)
    return await _get_member(db, ctx.org.id, member_id)


@router.post("/team/members/{member_id}/reject", response_model=MemberOut)
async def reject_member(member_id: uuid.UUID, ctx: Manager, db: DB):
    m = await _load_for_update(db, ctx.org.id, member_id)
    if m.status == "rejected":
        return await _get_member(db, ctx.org.id, member_id)
    if m.status != "pending":
        raise AppError(400, "invalid_state", "Só é possível recusar pedidos pendentes.")
    m.status = "rejected"
    await notify(
        db,
        m.promoter_id,
        "membership_rejected",
        "Pedido recusado",
        f"{ctx.org.name} não aprovou seu pedido para entrar na equipe.",
        "/promoter/perfil",
    )
    await db.commit()
    return await _get_member(db, ctx.org.id, member_id)


@router.post("/team/members/{member_id}/remove", response_model=MemberOut)
async def remove_member(member_id: uuid.UUID, ctx: Manager, db: DB):
    m = await _load_for_update(db, ctx.org.id, member_id)
    if m.status != "removed":
        m.status = "removed"
        await db.commit()
    return await _get_member(db, ctx.org.id, member_id)


@router.post("/team/members/{member_id}/adjust-points", response_model=MemberOut)
async def adjust_member_points(member_id: uuid.UUID, body: AdjustPointsIn, ctx: Manager, db: DB):
    try:
        await adjust_points(db, ctx.org.id, member_id, body.amount, body.reason, ctx.user.id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return await _get_member(db, ctx.org.id, member_id)


@router.get("/team/leaderboard", response_model=LeaderboardOut)
async def leaderboard(
    ctx: Manager,
    db: DB,
    period: Literal["all", "30d", "7d"] = "all",
    limit: int = Query(20, ge=1, le=100),
):
    entries = await lb.top_entries(db, ctx.org.id, period, limit)
    return LeaderboardOut(
        items=[
            LeaderboardEntryOut(
                rank=e.rank,
                membership_id=e.membership_id,
                name=e.name,
                instagram_username=e.instagram_username,
                points=e.points,
            )
            for e in entries
        ]
    )
