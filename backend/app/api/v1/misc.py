import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import Date, cast, func, select, update

from app.api.deps import DB, CurrentUser, Manager
from app.core.config import settings
from app.core.errors import not_found
from app.core.redis import get_redis
from app.models import (
    Campaign,
    InstagramAccount,
    Interaction,
    Membership,
    Notification,
    PointTransaction,
    Redemption,
)
from app.schemas.models import (
    ByDayOut,
    ConfigOut,
    DashboardKpisOut,
    LeaderboardEntryOut,
    ManagerDashboardOut,
    NotificationListOut,
    NotificationOut,
)
from app.services import leaderboard as lb
from app.services.views import interaction_out, interaction_query

router = APIRouter(tags=["misc"])


@router.get("/config", response_model=ConfigOut)
async def config():
    return ConfigOut(app_name="VIP Promoters", mock_mode=settings.meta_mock_mode)


@router.get("/health")
async def health():
    """Vivo (liveness): o processo responde. Nao toca banco nem Redis."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(db: DB):
    """Pronto (readiness): banco e Redis respondem. 503 se algum falhar, para o
    orquestrador tirar a instancia do balanceador em vez de servir erro."""
    checks: dict[str, str] = {}
    try:
        await db.execute(select(1))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "error"
    try:
        await get_redis().ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        checks["redis"] = "error"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "error", **checks}, status_code=200 if ok else 503
    )


# ------------------------------------------------------------------ dashboard


@router.get("/dashboard/manager", response_model=ManagerDashboardOut)
async def manager_dashboard(ctx: Manager, db: DB):
    org_id = ctx.org.id
    now = datetime.now(UTC)
    status_counts = dict(
        (
            await db.execute(
                select(Membership.status, func.count())
                .where(Membership.organization_id == org_id)
                .group_by(Membership.status)
            )
        ).all()
    )
    campaigns_active = await db.scalar(
        select(func.count())
        .select_from(Campaign)
        .where(Campaign.organization_id == org_id, Campaign.status == "active")
    )
    interactions_7d = await db.scalar(
        select(func.count())
        .select_from(Interaction)
        .where(
            Interaction.organization_id == org_id,
            Interaction.occurred_at >= now - timedelta(days=7),
        )
    )
    points_30d = await db.scalar(
        select(func.coalesce(func.sum(PointTransaction.amount), 0)).where(
            PointTransaction.organization_id == org_id,
            PointTransaction.type == "earn",
            PointTransaction.created_at >= now - timedelta(days=30),
        )
    )
    redemptions_pending = await db.scalar(
        select(func.count())
        .select_from(Redemption)
        .where(Redemption.organization_id == org_id, Redemption.status == "pending")
    )

    today = now.date()
    start_day = today - timedelta(days=13)
    start = datetime.combine(start_day, datetime.min.time(), tzinfo=UTC)
    day = cast(func.timezone("UTC", Interaction.occurred_at), Date)
    rows = await db.execute(
        select(day, Interaction.type, func.count())
        .where(Interaction.organization_id == org_id, Interaction.occurred_at >= start)
        .group_by(day, Interaction.type)
    )
    per_day: dict[date, dict[str, int]] = {}
    for d, t, n in rows:
        per_day.setdefault(d, {})[t] = n
    by_day = [
        ByDayOut(
            date=(start_day + timedelta(days=i)).isoformat(),
            comments=per_day.get(start_day + timedelta(days=i), {}).get("comment", 0),
            story_mentions=per_day.get(start_day + timedelta(days=i), {}).get("story_mention", 0),
        )
        for i in range(14)
    ]
    top = await lb.top_entries(db, org_id, "all", 5)
    recent = await db.execute(
        interaction_query()
        .where(Interaction.organization_id == org_id)
        .order_by(Interaction.occurred_at.desc(), Interaction.id)
        .limit(8)
    )
    has_account = await db.scalar(
        select(InstagramAccount.id).where(
            InstagramAccount.user_id == ctx.user.id, InstagramAccount.status == "active"
        )
    )
    return ManagerDashboardOut(
        instagram_connected=has_account is not None,
        kpis=DashboardKpisOut(
            promoters_approved=status_counts.get("approved", 0),
            promoters_pending=status_counts.get("pending", 0),
            campaigns_active=campaigns_active or 0,
            interactions_7d=interactions_7d or 0,
            points_issued_30d=int(points_30d or 0),
            redemptions_pending=redemptions_pending or 0,
        ),
        interactions_by_day=by_day,
        top_promoters=[
            LeaderboardEntryOut(
                rank=e.rank,
                membership_id=e.membership_id,
                name=e.name,
                instagram_username=e.instagram_username,
                points=e.points,
            )
            for e in top
        ],
        recent_interactions=[interaction_out(r) for r in recent],
    )


# ------------------------------------------------------------------ notificacoes


@router.get("/notifications", response_model=NotificationListOut)
async def list_notifications(user: CurrentUser, db: DB, limit: int = Query(20, ge=1, le=100)):
    rows = (
        (
            await db.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at.desc(), Notification.id)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    unread = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return NotificationListOut(
        items=[NotificationOut.model_validate(n) for n in rows], unread_count=unread or 0
    )


@router.post("/notifications/read-all", status_code=204)
async def read_all(user: CurrentUser, db: DB):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    await db.commit()
    return Response(status_code=204)


@router.post("/notifications/{notification_id}/read", status_code=204)
async def read_one(notification_id: uuid.UUID, user: CurrentUser, db: DB):
    owned = await db.scalar(
        select(Notification.id).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if owned is None:
        raise not_found()
    await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    await db.commit()
    return Response(status_code=204)
