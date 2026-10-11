import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Membership, PointTransaction, PromoterProfile, User
from app.models.base import TxType


@dataclass
class Entry:
    rank: int
    membership_id: uuid.UUID
    name: str
    instagram_username: str | None
    points: int


def _since(period: str) -> datetime | None:
    now = datetime.now(UTC)
    if period == "7d":
        return now - timedelta(days=7)
    if period == "30d":
        return now - timedelta(days=30)
    return None


def _ranked(org_id: uuid.UUID, period: str):
    """Subconsulta ranqueada: soma das transacoes `earn` no periodo (resgates nao reduzem)."""
    stmt = (
        select(
            Membership.id.label("membership_id"),
            User.name.label("name"),
            PromoterProfile.instagram_username.label("username"),
            func.sum(PointTransaction.amount).label("points"),
            func.max(PointTransaction.created_at).label("reached_at"),
        )
        .select_from(PointTransaction)
        .join(Membership, Membership.id == PointTransaction.membership_id)
        .join(User, User.id == Membership.promoter_id)
        .outerjoin(PromoterProfile, PromoterProfile.user_id == Membership.promoter_id)
        .where(
            PointTransaction.organization_id == org_id,
            PointTransaction.type == TxType.earn.value,
            Membership.status == "approved",
        )
        .group_by(Membership.id, User.name, PromoterProfile.instagram_username)
        .having(func.sum(PointTransaction.amount) > 0)
    )
    since = _since(period)
    if since is not None:
        stmt = stmt.where(PointTransaction.created_at >= since)
    inner = stmt.subquery()
    return (
        select(
            func.row_number()
            .over(order_by=(inner.c.points.desc(), inner.c.reached_at.asc(), inner.c.name.asc()))
            .label("rank"),
            inner.c.membership_id,
            inner.c.name,
            inner.c.username,
            inner.c.points,
        )
    ).subquery()


async def top_entries(db: AsyncSession, org_id: uuid.UUID, period: str, limit: int) -> list[Entry]:
    r = _ranked(org_id, period)
    res = await db.execute(select(r).order_by(r.c.rank).limit(limit))
    return [
        Entry(int(row.rank), row.membership_id, row.name, row.username, int(row.points))
        for row in res
    ]


async def rank_of(
    db: AsyncSession, org_id: uuid.UUID, period: str, membership_id: uuid.UUID
) -> tuple[int, int]:
    """(posicao, pontos) do membro; sem pontos no periodo fica depois de todos os listados."""
    r = _ranked(org_id, period)
    row = (
        await db.execute(select(r.c.rank, r.c.points).where(r.c.membership_id == membership_id))
    ).first()
    if row:
        return int(row[0]), int(row[1])
    total = await db.scalar(select(func.count()).select_from(r))
    return int(total or 0) + 1, 0
