import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rls
from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import ACCESS_COOKIE, decode_access_token
from app.core.sessions import is_revoked
from app.models import Membership, Organization, User

DB = Annotated[AsyncSession, Depends(get_db)]


async def current_user(request: Request, db: DB) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    decoded = decode_access_token(token) if token else None
    if decoded is None:
        raise AppError(401, "unauthenticated", "Faça login para continuar.")
    user_id, sid = decoded
    if await is_revoked(db, sid):
        raise AppError(401, "unauthenticated", "Faça login para continuar.")
    request.state.sid = sid
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "unauthenticated", "Faça login para continuar.")
    # RLS: daqui em diante a transacao so enxerga as organizacoes deste usuario (a dele,
    # se gestor; as equipes em que tem participacao, se promoter).
    org_ids = (
        await db.execute(
            select(Organization.id)
            .where(Organization.owner_id == user.id)
            .union(select(Membership.organization_id).where(Membership.promoter_id == user.id))
        )
    ).scalars()
    await rls.set_tenant(db, user.id, org_ids)
    return user


CurrentUser = Annotated[User, Depends(current_user)]


@dataclass
class ManagerCtx:
    user: User
    org: Organization


async def manager_ctx(user: CurrentUser, db: DB) -> ManagerCtx:
    if user.role != "manager":
        raise AppError(403, "forbidden", "Apenas gestores podem acessar este recurso.")
    org = (
        await db.execute(select(Organization).where(Organization.owner_id == user.id))
    ).scalar_one_or_none()
    if org is None:
        raise AppError(403, "forbidden", "Organização não encontrada.")
    return ManagerCtx(user, org)


Manager = Annotated[ManagerCtx, Depends(manager_ctx)]


async def promoter_user(user: CurrentUser) -> User:
    if user.role != "promoter":
        raise AppError(403, "forbidden", "Apenas promoters podem acessar este recurso.")
    return user


Promoter = Annotated[User, Depends(promoter_user)]


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=1_000_000)
) -> Pagination:
    return Pagination(limit, offset)


Pager = Annotated[Pagination, Depends(pagination)]


async def promoter_membership(db: AsyncSession, user: User, org_id: uuid.UUID | None) -> Membership:
    """Membro aprovado do promoter (na org informada ou, sem org_id, o mais antigo)."""
    stmt = select(Membership).where(
        Membership.promoter_id == user.id, Membership.status == "approved"
    )
    if org_id is not None:
        stmt = stmt.where(Membership.organization_id == org_id)
    else:
        stmt = stmt.order_by(Membership.joined_at)
    membership = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if membership is None:
        raise AppError(403, "membership_not_approved", "Você ainda não foi aprovado nesta equipe.")
    return membership
