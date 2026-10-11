"""Lojinha do gestor: recompensas e fila de resgates."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query, Response
from sqlalchemy import func, or_, select

from app.api.deps import DB, Manager, Pager
from app.core.errors import not_found
from app.models import Redemption, Reward, User
from app.schemas.common import Page
from app.schemas.models import (
    NoteIn,
    RedemptionOut,
    RewardCreateIn,
    RewardOut,
    RewardPatchIn,
)
from app.services import rewards as svc
from app.services.views import (
    load_redemption,
    redeemed_counts,
    redemption_out,
    redemption_query,
    reward_out,
)

router = APIRouter(tags=["shop"])


async def _get_reward(db, org_id: uuid.UUID, reward_id: uuid.UUID, *, lock: bool = False) -> Reward:
    stmt = select(Reward).where(
        Reward.id == reward_id, Reward.organization_id == org_id, Reward.archived_at.is_(None)
    )
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    reward = (await db.execute(stmt)).scalar_one_or_none()
    if reward is None:
        raise not_found("Recompensa não encontrada.")
    return reward


@router.get("/rewards", response_model=Page[RewardOut])
async def list_rewards(ctx: Manager, db: DB, page: Pager, include_inactive: bool = False):
    where = [Reward.organization_id == ctx.org.id, Reward.archived_at.is_(None)]
    if not include_inactive:
        where.append(Reward.is_active.is_(True))
    total = await db.scalar(select(func.count()).select_from(Reward).where(*where))
    rows = (
        (
            await db.execute(
                select(Reward)
                .where(*where)
                .order_by(Reward.created_at.desc(), Reward.id)
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    counts = await redeemed_counts(db, [r.id for r in rows])
    return Page[RewardOut](
        items=[reward_out(r, counts.get(r.id, 0)) for r in rows], total=total or 0
    )


@router.post("/rewards", status_code=201, response_model=RewardOut)
async def create_reward(body: RewardCreateIn, ctx: Manager, db: DB):
    reward = Reward(organization_id=ctx.org.id, **body.model_dump())
    db.add(reward)
    await db.commit()
    return reward_out(reward, 0)


@router.patch("/rewards/{reward_id}", response_model=RewardOut)
async def patch_reward(reward_id: uuid.UUID, body: RewardPatchIn, ctx: Manager, db: DB):
    reward = await _get_reward(db, ctx.org.id, reward_id, lock=True)
    for field in body.model_fields_set:
        value = getattr(body, field)
        if value is None and field in ("name", "cost_points", "is_active"):
            continue
        setattr(reward, field, value)
    await db.commit()
    counts = await redeemed_counts(db, [reward.id])
    return reward_out(reward, counts.get(reward.id, 0))


@router.delete("/rewards/{reward_id}", status_code=204)
async def delete_reward(reward_id: uuid.UUID, ctx: Manager, db: DB):
    reward = await _get_reward(db, ctx.org.id, reward_id, lock=True)
    has = await db.scalar(
        select(func.count()).select_from(Redemption).where(Redemption.reward_id == reward.id)
    )
    if has:
        reward.archived_at = datetime.now(UTC)
        reward.is_active = False
    else:
        await db.delete(reward)
    await db.commit()
    return Response(status_code=204)


@router.get("/redemptions", response_model=Page[RedemptionOut])
async def list_redemptions(
    ctx: Manager,
    db: DB,
    page: Pager,
    status: Literal["pending", "fulfilled", "cancelled"] | None = None,
    search: str | None = Query(None, max_length=100),
):
    where = [Redemption.organization_id == ctx.org.id]
    if status:
        where.append(Redemption.status == status)
    if search and search.strip():
        term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{term}%"
        where.append(
            or_(
                Redemption.code.ilike(like, escape="\\"),
                User.name.ilike(like, escape="\\"),
                Reward.name.ilike(like, escape="\\"),
            )
        )
    base = redemption_query().where(*where)
    total = await db.scalar(
        select(func.count()).select_from(base.with_only_columns(Redemption.id).subquery())
    )
    rows = await db.execute(
        base.order_by(Redemption.created_at.desc(), Redemption.id)
        .limit(page.limit)
        .offset(page.offset)
    )
    return Page[RedemptionOut](
        items=[redemption_out(r, manager_view=True) for r in rows], total=total or 0
    )


@router.post("/redemptions/{redemption_id}/fulfill", response_model=RedemptionOut)
async def fulfill(redemption_id: uuid.UUID, ctx: Manager, db: DB, body: NoteIn | None = None):
    try:
        await svc.fulfill(db, ctx.org.id, redemption_id, ctx.user.id, body.note if body else None)
    except Exception:
        await db.rollback()
        raise
    return await load_redemption(db, redemption_id, manager_view=True)


@router.post("/redemptions/{redemption_id}/cancel", response_model=RedemptionOut)
async def cancel(redemption_id: uuid.UUID, ctx: Manager, db: DB, body: NoteIn | None = None):
    await svc.cancel(db, ctx.org.id, redemption_id, ctx.user.id, body.note if body else None)
    return await load_redemption(db, redemption_id, manager_view=True)
