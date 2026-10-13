"""Verificacao de posse do @ do Instagram por codigo em comentario, e disputa de @.

Por que assim: o login do Instagram (Instagram API with Instagram Login) so aceita contas
PROFISSIONAIS, e a maioria dos promoters tem conta pessoal. Ja o comentario chega pelo webhook
da conta do gestor com o @ AUTENTICO de quem comentou (o dado vem da Meta, nao do usuario).
Entao: o app gera um codigo (VIP-XXXXXX); quem comenta esse codigo em qualquer post de uma
conta conectada prova que controla o @ que aparece no comentario.

Disputa: se outra pessoa cadastrou o seu @ sem verificar, voce pede o @ (claim) e comenta o
codigo. Ao confirmar, o @ passa para voce, verificado; quem estava com ele fica sem @ e as
equipes dele voltam para "pendente". Um @ ja VERIFICADO nao pode ser reivindicado.
"""

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Membership, Organization, PromoterProfile, User, UsernameClaim
from app.services.notifications import notify

CLAIM_TTL = timedelta(hours=48)
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sem 0 O 1 I L
CODE_RE = re.compile(r"\bVIP-([A-HJ-NP-Z2-9]{6})\b", re.IGNORECASE)


def new_code() -> str:
    return "VIP-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


def find_code(text: str | None) -> str | None:
    if not text:
        return None
    m = CODE_RE.search(text)
    return f"VIP-{m.group(1).upper()}" if m else None


async def pending_claim(db: AsyncSession, user_id: uuid.UUID) -> UsernameClaim | None:
    return (
        await db.execute(
            select(UsernameClaim).where(
                UsernameClaim.user_id == user_id,
                UsernameClaim.status == "pending",
                UsernameClaim.expires_at > datetime.now(UTC),
            )
        )
    ).scalar_one_or_none()


async def _expire_open_claims(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(UsernameClaim)
        .where(UsernameClaim.user_id == user_id, UsernameClaim.status == "pending")
        .values(status="expired")
    )


async def start_claim(db: AsyncSession, user_id: uuid.UUID, username: str) -> UsernameClaim:
    """Abre (ou reaproveita) o pedido de verificacao do @ informado. Nao faz commit.

    O @ pode ser o proprio (verificacao) ou um @ cadastrado por outra pessoa sem
    verificacao (disputa). @ verificado por outra pessoa e recusado."""
    holder = (
        await db.execute(
            select(PromoterProfile).where(PromoterProfile.instagram_username == username)
        )
    ).scalar_one_or_none()
    if holder is not None and holder.user_id != user_id and holder.verified:
        raise AppError(
            409,
            "instagram_username_verified",
            "Este @ já foi verificado por outra pessoa. Se ele é seu, fale com o suporte.",
        )
    if holder is not None and holder.user_id == user_id and holder.verified:
        raise AppError(409, "already_verified", "Seu @ já está verificado.")
    current = await pending_claim(db, user_id)
    if current is not None and current.instagram_username == username:
        return current
    await _expire_open_claims(db, user_id)
    await db.flush()
    claim = UsernameClaim(
        user_id=user_id,
        instagram_username=username,
        code=new_code(),
        status="pending",
        expires_at=datetime.now(UTC) + CLAIM_TTL,
    )
    db.add(claim)
    await db.flush()
    return claim


async def cancel_claims(db: AsyncSession, user_id: uuid.UUID) -> None:
    await _expire_open_claims(db, user_id)


async def _back_to_pending(db: AsyncSession, user: User, reason: str) -> None:
    """Toda troca de @ volta as equipes aprovadas para pendente (o gestor e o portao)."""
    rows = (
        await db.execute(
            select(Membership, Organization.owner_id)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(Membership.promoter_id == user.id, Membership.status == "approved")
            .with_for_update(of=Membership)
        )
    ).all()
    for m, owner_id in rows:
        m.status = "pending"
        m.approved_at = None
        m.approved_by = None
        await notify(
            db,
            owner_id,
            "username_changed",
            "Promoter precisa de nova aprovação",
            f"{user.name} {reason} e precisa de nova aprovação.",
            "/gestor/equipe",
        )


async def confirm_by_comment(
    db: AsyncSession, code: str, commenter_username: str | None, commenter_id: str | None
) -> bool:
    """Chamado pelo pipeline quando um comentario traz um codigo. Nao faz commit.
    Devolve True se verificou algum @."""
    if not commenter_username:
        return False
    claim = (
        await db.execute(
            select(UsernameClaim)
            .where(
                UsernameClaim.code == code,
                UsernameClaim.status == "pending",
                UsernameClaim.expires_at > datetime.now(UTC),
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if claim is None or claim.instagram_username != commenter_username:
        return False
    profile = (
        await db.execute(
            select(PromoterProfile)
            .where(PromoterProfile.user_id == claim.user_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    user = await db.get(User, claim.user_id)
    if profile is None or user is None:
        return False
    now = datetime.now(UTC)
    username = claim.instagram_username

    holder = (
        await db.execute(
            select(PromoterProfile)
            .where(
                PromoterProfile.instagram_username == username,
                PromoterProfile.user_id != claim.user_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if holder is not None:
        if holder.verified:  # verificou no meio do caminho: a disputa perde
            claim.status = "expired"
            return False
        holder_user = await db.get(User, holder.user_id)
        holder.instagram_username = None
        holder.verified = False
        holder.verified_at = None
        holder.verification_method = None
        holder.ig_scoped_id = None
        await db.flush()  # libera o @ (unico) antes de entregar ao novo dono
        if holder_user is not None:
            await _back_to_pending(db, holder_user, f"perdeu o @{username} numa disputa")
            await notify(
                db,
                holder_user.id,
                "username_lost",
                "Seu @ foi reivindicado",
                f"O dono de @{username} provou a posse pelo Instagram. Cadastre o seu @ "
                "verdadeiro no perfil para voltar a pontuar.",
                "/promoter/perfil",
            )

    if profile.instagram_username != username:
        old = profile.instagram_username
        profile.instagram_username = username
        await _back_to_pending(
            db, user, f"assumiu o @{username}" + (f" (antes @{old})" if old else "")
        )
    profile.verified = True
    profile.verified_at = now
    profile.verification_method = "comment"
    if commenter_id:
        profile.ig_scoped_id = commenter_id
    claim.status = "verified"
    claim.verified_at = now
    await notify(
        db,
        user.id,
        "username_verified",
        "Seu @ foi verificado",
        f"Confirmamos que @{username} é seu.",
        "/promoter/perfil",
    )
    await db.flush()
    return True
