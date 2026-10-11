"""Resgates. Ordem de locks (sempre a mesma): resgate -> membro -> recompensa."""

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, not_found
from app.models import Membership, Organization, Redemption, Reward
from app.models.base import RedemptionStatus, TxType
from app.services.notifications import notify
from app.services.points import apply_transaction, lock_membership

_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def new_redemption_code() -> str:
    return "VIP-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


async def _existing(db: AsyncSession, membership_id: uuid.UUID, request_id: uuid.UUID):
    res = await db.execute(
        select(Redemption).where(
            Redemption.membership_id == membership_id, Redemption.request_id == request_id
        )
    )
    return res.scalar_one_or_none()


async def redeem(
    db: AsyncSession, membership_id: uuid.UUID, reward_id: uuid.UUID, request_id: uuid.UUID
) -> Redemption:
    """Resgata uma recompensa numa unica transacao. Faz commit.

    Idempotente por (membro, request_id): repetir devolve o resgate original.
    """
    try:
        return await _redeem(db, membership_id, reward_id, request_id)
    except IntegrityError:
        await db.rollback()
        again = await _existing(db, membership_id, request_id)
        if again is not None:
            return again
        raise
    except Exception:
        await db.rollback()
        raise


async def _redeem(
    db: AsyncSession, membership_id: uuid.UUID, reward_id: uuid.UUID, request_id: uuid.UUID
) -> Redemption:
    membership = await lock_membership(db, membership_id)
    if membership is None or membership.status != "approved":
        raise AppError(403, "membership_not_approved", "Você ainda não foi aprovado nesta equipe.")
    again = await _existing(db, membership.id, request_id)
    if again is not None:
        await db.commit()  # libera o lock; resposta idempotente
        return again
    reward = (
        await db.execute(
            select(Reward)
            .where(Reward.id == reward_id, Reward.organization_id == membership.organization_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if reward is None:
        raise not_found("Recompensa não encontrada.")
    if not reward.is_active or reward.archived_at is not None:
        raise AppError(400, "reward_unavailable", "Esta recompensa não está disponível.")
    if reward.stock is not None and reward.stock <= 0:
        raise AppError(400, "out_of_stock", "Recompensa esgotada.")
    if reward.max_per_promoter is not None:
        mine = await db.scalar(
            select(func.count())
            .select_from(Redemption)
            .where(
                Redemption.membership_id == membership.id,
                Redemption.reward_id == reward.id,
                Redemption.status != RedemptionStatus.cancelled.value,
            )
        )
        if (mine or 0) >= reward.max_per_promoter:
            raise AppError(
                400,
                "redeem_limit_reached",
                "Você já atingiu o limite de resgates desta recompensa.",
            )
    redemption = Redemption(
        id=uuid.uuid4(),
        organization_id=membership.organization_id,
        reward_id=reward.id,
        membership_id=membership.id,
        request_id=request_id,
        cost_points=reward.cost_points,
        status=RedemptionStatus.pending.value,
        code=new_redemption_code(),
    )
    db.add(redemption)
    await db.flush()
    await apply_transaction(
        db,
        membership,
        -reward.cost_points,
        TxType.redeem,
        f"Resgate: {reward.name}",
        redemption_id=redemption.id,
    )
    if reward.stock is not None:
        reward.stock -= 1
    owner = await db.scalar(
        select(Organization.owner_id).where(Organization.id == membership.organization_id)
    )
    if owner is not None:
        await notify(
            db,
            owner,
            "redemption_requested",
            "Novo pedido de resgate",
            f"Há um novo resgate pendente: {reward.name}.",
            "/gestor/resgates",
        )
    await db.commit()
    return redemption


async def _lock_redemption(
    db: AsyncSession, org_id: uuid.UUID, redemption_id: uuid.UUID
) -> Redemption:
    r = (
        await db.execute(
            select(Redemption)
            .where(Redemption.id == redemption_id, Redemption.organization_id == org_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if r is None:
        raise not_found()
    if r.status != RedemptionStatus.pending.value:
        raise AppError(400, "redemption_not_pending", "Este resgate já foi resolvido.")
    return r


async def fulfill(
    db: AsyncSession, org_id: uuid.UUID, redemption_id: uuid.UUID, by: uuid.UUID, note: str | None
) -> Redemption:
    r = await _lock_redemption(db, org_id, redemption_id)
    r.status = RedemptionStatus.fulfilled.value
    r.resolved_at = datetime.now(UTC)
    r.resolved_by = by
    r.note = note
    promoter_id = await db.scalar(
        select(Membership.promoter_id).where(Membership.id == r.membership_id)
    )
    reward_name = await db.scalar(select(Reward.name).where(Reward.id == r.reward_id))
    if promoter_id:
        await notify(
            db,
            promoter_id,
            "redemption_fulfilled",
            "Resgate entregue",
            f"Seu resgate de {reward_name} foi marcado como entregue ({r.code}).",
            "/promoter/resgates",
        )
    await db.commit()
    return r


async def cancel(
    db: AsyncSession, org_id: uuid.UUID, redemption_id: uuid.UUID, by: uuid.UUID, note: str | None
) -> Redemption:
    try:
        r = await _lock_redemption(db, org_id, redemption_id)
        membership = await lock_membership(db, r.membership_id)
        reward = (
            await db.execute(
                select(Reward)
                .where(Reward.id == r.reward_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        if membership is None:
            raise not_found()
        await apply_transaction(
            db,
            membership,
            r.cost_points,
            TxType.refund,
            f"Estorno do resgate: {reward.name}",
            redemption_id=r.id,
            created_by=by,
        )
        if reward.stock is not None:
            reward.stock += 1
        r.status = RedemptionStatus.cancelled.value
        r.resolved_at = datetime.now(UTC)
        r.resolved_by = by
        r.note = note
        await notify(
            db,
            membership.promoter_id,
            "redemption_cancelled",
            "Resgate cancelado",
            f"Seu resgate de {reward.name} foi cancelado e os pontos foram devolvidos.",
            "/promoter/resgates",
        )
        await db.commit()
        return r
    except Exception:
        await db.rollback()
        raise
