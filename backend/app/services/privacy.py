"""Exclusao de conta e de dados (LGPD art. 18; callback de data deletion da Meta).

Principio: o que identifica uma pessoa sai; o que e contabilidade do gestor (pontos ja
creditados, resgates de OUTRAS pessoas) fica. Interacoes sao ANONIMIZADAS (mesma funcao da
politica de retencao), nunca apagadas: apagar quebraria o extrato de quem nao pediu nada.
"""

import asyncio
import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import ColumnElement, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Campaign,
    DataDeletionRequest,
    InstagramAccount,
    Interaction,
    Membership,
    Organization,
    PromoterProfile,
    Redemption,
    Reward,
    User,
)
from app.models.base import RedemptionStatus
from app.services.retention import PERSONAL_FIELDS
from app.services.uploads import resolve_path

log = logging.getLogger("app.privacy")


def subject_hash(ig_user_id: str) -> str:
    return hashlib.sha256(f"ig:{ig_user_id}".encode()).hexdigest()


async def anonymize_interactions(db: AsyncSession, *conds: ColumnElement[bool]) -> int:
    """Apaga texto, @, id do Instagram e link da midia das interacoes que casam com
    QUALQUER das condicoes. Nao faz commit."""
    if not conds:
        return 0
    res = await db.execute(
        update(Interaction)
        .where(or_(*conds))
        .values(**PERSONAL_FIELDS)
        .execution_options(synchronize_session=False)
    )
    return res.rowcount or 0


def _local_upload_files(urls: list[str | None]) -> list[Path]:
    prefix = f"{settings.app_base_url}/api/v1/uploads/"
    paths = []
    for url in urls:
        if url and url.startswith(prefix):
            path = resolve_path(url.removeprefix(prefix))
            if path is not None:
                paths.append(path)
    return paths


async def _remove_files(paths: list[Path]) -> None:
    def _rm() -> None:
        for p in paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                log.warning("upload nao removido", extra={"event": "privacy"})

    if paths:
        await asyncio.to_thread(_rm)


# ------------------------------------------------------------------ conta


@dataclass
class DeletionSummary:
    interactions_anonymized: int = 0
    redemptions_cancelled: int = 0
    files_removed: int = 0
    family_ids: set[uuid.UUID] = field(default_factory=set)


async def delete_account(db: AsyncSession, user: User) -> DeletionSummary:
    """Exclui a conta e os dados pessoais dela. Faz commit.

    - Gestor: a organizacao inteira sai (equipe, campanhas, interacoes, lojinha, resgates),
      junto com a conexao do Instagram e as imagens enviadas.
    - Promoter: perfil, participacoes, saldo, extrato e resgates saem; as interacoes dele nas
      equipes sao anonimizadas (o numero do gestor continua batendo); resgates pendentes
      devolvem o estoque da recompensa.
    """
    from app.models import RefreshToken  # evita ciclo de import

    out = DeletionSummary()
    out.family_ids = set(
        (
            await db.execute(
                select(RefreshToken.family_id).where(RefreshToken.user_id == user.id).distinct()
            )
        ).scalars()
    )
    files: list[Path] = []
    if user.role == "manager":
        org = (
            await db.execute(select(Organization).where(Organization.owner_id == user.id))
        ).scalar_one_or_none()
        if org is not None:
            urls = list(
                (
                    await db.execute(
                        select(Reward.image_url).where(Reward.organization_id == org.id)
                    )
                ).scalars()
            )
            urls += list(
                (
                    await db.execute(
                        select(Campaign.publish_image_url).where(Campaign.organization_id == org.id)
                    )
                ).scalars()
            )
            files = _local_upload_files(urls)
            # resgates referenciam recompensas com RESTRICT: saem antes da organizacao
            await db.execute(delete(Redemption).where(Redemption.organization_id == org.id))
            await db.execute(delete(Organization).where(Organization.id == org.id))
        await db.execute(delete(InstagramAccount).where(InstagramAccount.user_id == user.id))
    else:
        profile = await db.get(PromoterProfile, user.id)
        membership_ids = list(
            (
                await db.execute(select(Membership.id).where(Membership.promoter_id == user.id))
            ).scalars()
        )
        conds: list[ColumnElement[bool]] = []
        if membership_ids:
            conds.append(Interaction.membership_id.in_(membership_ids))
        if profile is not None and profile.instagram_username:
            conds.append(Interaction.ig_username == profile.instagram_username)
        if profile is not None and profile.ig_scoped_id:
            conds.append(Interaction.ig_scoped_id == profile.ig_scoped_id)
        out.interactions_anonymized = await anonymize_interactions(db, *conds)
        if membership_ids:
            pending = (
                (
                    await db.execute(
                        select(Redemption.reward_id).where(
                            Redemption.membership_id.in_(membership_ids),
                            Redemption.status == RedemptionStatus.pending.value,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for reward_id in pending:
                await db.execute(
                    update(Reward)
                    .where(Reward.id == reward_id, Reward.stock.is_not(None))
                    .values(stock=Reward.stock + 1)
                )
            out.redemptions_cancelled = len(pending)
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()
    await _remove_files(files)
    out.files_removed = len(files)
    log.info("conta excluida", extra={"event": "account_deleted"})
    return out


# ------------------------------------------------------------------ Meta


async def forget_instagram_user(db: AsyncSession, ig_user_id: str) -> int:
    """Apaga o que o app guarda sobre um id do Instagram que autorizou o app. Nao faz
    commit; devolve quantos registros foram removidos ou anonimizados."""
    removed = 0
    account = (
        await db.execute(select(InstagramAccount).where(InstagramAccount.ig_user_id == ig_user_id))
    ).scalar_one_or_none()
    if account is not None:
        # Gestor: os dados vieram pelo token dele (comentarios nos posts, midia dos posts).
        org_id = await db.scalar(
            select(Organization.id).where(Organization.owner_id == account.user_id)
        )
        if org_id is not None:
            removed += await anonymize_interactions(db, Interaction.organization_id == org_id)
            res = await db.execute(
                update(Campaign)
                .where(Campaign.organization_id == org_id)
                .values(media_url=None, thumbnail_url=None, caption=None, permalink=None)
            )
            removed += res.rowcount or 0
        await db.delete(account)
        removed += 1
    # Promoter verificado pelo login do Instagram (fluxo antigo) ou quem comentou.
    res = await db.execute(
        update(PromoterProfile)
        .where(PromoterProfile.ig_scoped_id == ig_user_id)
        .values(ig_scoped_id=None, verified=False, verified_at=None, verification_method=None)
    )
    removed += res.rowcount or 0
    removed += await anonymize_interactions(db, Interaction.ig_scoped_id == ig_user_id)
    return removed


async def handle_meta_data_deletion(db: AsyncSession, ig_user_id: str) -> DataDeletionRequest:
    """Atende o callback de exclusao de dados e registra o pedido. Faz commit."""
    removed = await forget_instagram_user(db, ig_user_id) if ig_user_id else 0
    now = datetime.now(UTC)
    req = DataDeletionRequest(
        confirmation_code=secrets.token_urlsafe(12),
        subject_hash=subject_hash(ig_user_id or "?"),
        status="completed",
        items_removed=removed,
        requested_at=now,
        completed_at=now,
    )
    db.add(req)
    await db.commit()
    return req


async def forget_instagram_username(db: AsyncSession, username: str) -> int:
    """Pedido de terceiro (quem comentou, sem conta no app) feito por e-mail ao suporte:
    anonimiza tudo o que o app guarda com esse @. Uso: `python -m app.cli esquecer @fulano`.
    Faz commit."""
    username = username.strip().lstrip("@").lower()
    n = await anonymize_interactions(db, Interaction.ig_username == username)
    await db.commit()
    return n
