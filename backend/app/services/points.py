"""Razao de pontos. Toda mudanca de saldo passa por apply_transaction com o membro travado."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Membership, PointTransaction
from app.models.base import TxType


async def lock_membership(
    db: AsyncSession, membership_id: uuid.UUID, organization_id: uuid.UUID | None = None
) -> Membership | None:
    """SELECT ... FOR UPDATE do membro (refresca o objeto caso ja esteja na sessao)."""
    stmt = select(Membership).where(Membership.id == membership_id)
    if organization_id is not None:
        stmt = stmt.where(Membership.organization_id == organization_id)
    result = await db.execute(stmt.with_for_update().execution_options(populate_existing=True))
    return result.scalar_one_or_none()


async def apply_transaction(
    db: AsyncSession,
    membership: Membership,
    amount: int,
    type_: TxType,
    description: str,
    *,
    interaction_id: uuid.UUID | None = None,
    redemption_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
    insufficient_message: str = "Você não tem pontos suficientes.",
) -> PointTransaction:
    """Escreve a linha do extrato e atualiza o saldo. O chamador DEVE ter travado o membro."""
    if amount == 0:
        raise ValueError("amount must be non-zero")
    new_balance = membership.points_balance + amount
    if new_balance < 0:
        raise AppError(400, "insufficient_points", insufficient_message)
    membership.points_balance = new_balance
    if type_ == TxType.earn:
        membership.total_earned += amount
    tx = PointTransaction(
        organization_id=membership.organization_id,
        membership_id=membership.id,
        amount=amount,
        type=type_.value,
        description=description[:255],
        balance_after=new_balance,
        interaction_id=interaction_id,
        redemption_id=redemption_id,
        created_by=created_by,
    )
    db.add(tx)
    await db.flush()
    return tx


async def adjust_points(
    db: AsyncSession,
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    amount: int,
    reason: str,
    by: uuid.UUID,
) -> Membership:
    """Ajuste manual do gestor. Nao confirma a transacao (o chamador faz commit)."""
    membership = await lock_membership(db, membership_id, organization_id)
    if membership is None:
        raise AppError(404, "not_found", "Recurso não encontrado.")
    if membership.status != "approved":
        raise AppError(400, "membership_not_approved", "O promoter ainda não está aprovado.")
    await apply_transaction(
        db,
        membership,
        amount,
        TxType.adjust,
        f"Ajuste do gestor: {reason}",
        created_by=by,
        insufficient_message="O ajuste deixaria o saldo negativo.",
    )
    return membership
