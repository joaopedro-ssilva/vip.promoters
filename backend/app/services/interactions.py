"""Pipeline de interacoes: webhooks, polling e simulador usam process_event()."""

import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rls
from app.core.crypto import decrypt
from app.models import (
    Campaign,
    InstagramAccount,
    Interaction,
    Membership,
    Organization,
    PromoterProfile,
)
from app.models.base import (
    AccountStatus,
    CampaignStatus,
    InteractionStatus,
    InteractionType,
    TxType,
)
from app.services import verification
from app.services.instagram import get_instagram_client
from app.services.instagram.base import (
    InstagramAuthError,
    InstagramError,
    InstagramRateLimitError,
)
from app.services.notifications import notify
from app.services.points import apply_transaction, lock_membership

log = logging.getLogger("app.pipeline")

START_TOLERANCE = timedelta(seconds=30)
REMATCH_BATCH = 200
_USERNAME_RE = re.compile(r"^[a-z0-9._]{1,30}$")


class TransientPipelineError(Exception):
    """Falha temporaria: o job deve ser repetido (nada foi gravado)."""


def normalize_username(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lstrip("@").lower()
    return v if _USERNAME_RE.match(v) else (v[:64] or None)


@dataclass
class InboundEvent:
    type: str  # comment | story_mention
    ig_event_id: str
    account_ig_id: str  # entry.id: o ig_user_id do gestor
    occurred_at: datetime
    from_id: str | None = None
    from_username: str | None = None
    media_id: str | None = None
    text: str | None = None
    parent_id: str | None = None
    media_url: str | None = None


@dataclass
class PipelineResult:
    outcome: str  # created | exists | dropped
    interaction: Interaction | None = None


# ------------------------------------------------------------------ consultas


async def _get_existing(db: AsyncSession, type_: str, event_id: str) -> Interaction | None:
    res = await db.execute(
        select(Interaction).where(Interaction.type == type_, Interaction.ig_event_id == event_id)
    )
    return res.scalar_one_or_none()


async def _load_account(
    db: AsyncSession, ig_user_id: str
) -> tuple[InstagramAccount, Organization] | None:
    res = await db.execute(
        select(InstagramAccount, Organization)
        .join(Organization, Organization.owner_id == InstagramAccount.user_id)
        .where(InstagramAccount.ig_user_id == ig_user_id, InstagramAccount.status != "revoked")
    )
    row = res.first()
    return (row[0], row[1]) if row else None


async def _find_comment_campaign(
    db: AsyncSession, org_id: uuid.UUID, media_id: str
) -> Campaign | None:
    """Prefere a campanha nao encerrada (ha no maximo uma por post)."""
    res = await db.execute(
        select(Campaign)
        .where(
            Campaign.organization_id == org_id,
            Campaign.ig_media_id == media_id,
            Campaign.status != CampaignStatus.draft.value,
        )
        .order_by(
            (Campaign.status == CampaignStatus.active.value).desc(), Campaign.created_at.desc()
        )
        .limit(1)
    )
    return res.scalar_one_or_none()


def _in_window(c: Campaign, at: datetime) -> bool:
    if c.status != CampaignStatus.active.value:
        return False
    # tolerancia: os eventos chegam com precisao de segundos e ha diferenca de relogio
    if c.starts_at and at < c.starts_at - START_TOLERANCE:
        return False
    return not (c.ends_at and at > c.ends_at)


async def _story_candidates(db: AsyncSession, org_id: uuid.UUID, at: datetime) -> list[Campaign]:
    res = await db.execute(
        select(Campaign)
        .where(
            Campaign.organization_id == org_id,
            Campaign.status == CampaignStatus.active.value,
            Campaign.points_story_mention > 0,
            or_(Campaign.starts_at.is_(None), Campaign.starts_at <= at + START_TOLERANCE),
            or_(Campaign.ends_at.is_(None), Campaign.ends_at >= at),
        )
        .order_by(Campaign.dispatched_at.desc().nulls_last(), Campaign.created_at.desc())
    )
    return list(res.scalars())


async def _match_membership(
    db: AsyncSession, org_id: uuid.UUID, from_id: str | None, username: str | None
) -> Membership | None:
    conds = []
    if from_id:
        conds.append(PromoterProfile.ig_scoped_id == from_id)
    if username:
        conds.append(PromoterProfile.instagram_username == username)
    if not conds:
        return None
    scoped_first = (
        (PromoterProfile.ig_scoped_id == from_id).desc() if from_id else Membership.joined_at
    )
    res = await db.execute(
        select(Membership)
        .join(PromoterProfile, PromoterProfile.user_id == Membership.promoter_id)
        .where(
            Membership.organization_id == org_id,
            Membership.status == "approved",
            or_(*conds),
        )
        .order_by(scoped_first)
        .limit(1)
    )
    return res.scalar_one_or_none()


# ------------------------------------------------------------------ premiacao


async def _award(
    db: AsyncSession, it: Interaction, campaign: Campaign, membership: Membership, points: int
) -> None:
    it.membership_id = membership.id
    it.campaign_id = campaign.id
    it.status = InteractionStatus.awarded.value
    it.points_awarded = points
    await db.flush()  # pode violar o indice unico parcial (corrida)
    what = "Comentário" if it.type == InteractionType.comment.value else "Menção no story"
    await apply_transaction(
        db,
        membership,
        points,
        TxType.earn,
        f"{what} na campanha {campaign.title}",
        interaction_id=it.id,
    )
    await notify(
        db,
        membership.promoter_id,
        "points_earned",
        f"Você ganhou {points} pontos",
        f"{what} na campanha {campaign.title}.",
        f"/promoter/campanhas/{campaign.id}",
    )


def _eligible(m: Membership, at: datetime) -> bool:
    """Membro ainda aprovado. Se foi aprovado automaticamente (sem aprovacao do gestor), so
    ganha por eventos posteriores a entrada dele: a aprovacao manual e a prova de identidade
    do @ e so ela permite creditar eventos anteriores."""
    if m.status != "approved":
        return False
    if m.approved_by is not None:
        return True
    return at >= m.joined_at - START_TOLERANCE


def _no_award(it: Interaction, status: InteractionStatus, membership_id: uuid.UUID | None) -> None:
    it.membership_id = membership_id
    it.status = status.value
    it.points_awarded = 0


async def _decide_comment(
    db: AsyncSession, it: Interaction, campaign_id: uuid.UUID, membership_id: uuid.UUID
) -> None:
    """Decide apos travar o membro e REVALIDAR elegibilidade, campanha e janela."""
    membership = await lock_membership(db, membership_id)
    campaign = await db.get(Campaign, campaign_id, populate_existing=True)
    if membership is None or not _eligible(membership, it.occurred_at):
        _no_award(it, InteractionStatus.unmatched, None)
        await db.flush()
        return
    if campaign is None or campaign.points_comment <= 0 or not _in_window(campaign, it.occurred_at):
        _no_award(it, InteractionStatus.out_of_window, membership.id)
        await db.flush()
        return
    already = await db.scalar(
        select(
            exists().where(
                Interaction.campaign_id == campaign.id,
                Interaction.membership_id == membership.id,
                Interaction.type == InteractionType.comment.value,
                Interaction.status == InteractionStatus.awarded.value,
                Interaction.id != it.id,
            )
        )
    )
    if already:
        _no_award(it, InteractionStatus.duplicate, membership.id)
        await db.flush()
        return
    await _award(db, it, campaign, membership, campaign.points_comment)


async def _decide_story(db: AsyncSession, it: Interaction, membership_id: uuid.UUID) -> None:
    membership = await lock_membership(db, membership_id)
    if membership is None or not _eligible(membership, it.occurred_at):
        _no_award(it, InteractionStatus.unmatched, None)
        await db.flush()
        return
    # candidatas recalculadas DEPOIS do lock (podem ter mudado desde a leitura inicial)
    candidates = await _story_candidates(db, it.organization_id, it.occurred_at)
    if not candidates:
        it.campaign_id = None
        _no_award(it, InteractionStatus.out_of_window, membership.id)
        await db.flush()
        return
    counts_res = await db.execute(
        select(Interaction.campaign_id, func.count())
        .where(
            Interaction.membership_id == membership.id,
            Interaction.type == InteractionType.story_mention.value,
            Interaction.status == InteractionStatus.awarded.value,
            Interaction.campaign_id.in_([c.id for c in candidates]),
            Interaction.id != it.id,
        )
        .group_by(Interaction.campaign_id)
    )
    counts = dict(counts_res.all())
    for c in candidates:
        if counts.get(c.id, 0) < c.max_story_mentions:
            await _award(db, it, c, membership, c.points_story_mention)
            return
    it.campaign_id = candidates[0].id
    _no_award(it, InteractionStatus.duplicate, membership.id)
    await db.flush()


# ------------------------------------------------------------------ persistencia


def _clone(it: Interaction, status: str) -> Interaction:
    return Interaction(
        organization_id=it.organization_id,
        campaign_id=it.campaign_id,
        membership_id=it.membership_id,
        type=it.type,
        ig_event_id=it.ig_event_id,
        ig_username=it.ig_username,
        ig_scoped_id=it.ig_scoped_id,
        text=it.text,
        media_url=it.media_url,
        occurred_at=it.occurred_at,
        status=status,
        points_awarded=0,
    )


async def _persist(
    db: AsyncSession,
    it: Interaction,
    decide: Callable[[Interaction], Awaitable[None]] | None,
    lock_membership_id: uuid.UUID | None = None,
) -> PipelineResult:
    """Insere a interacao num savepoint; corridas viram `exists` ou `duplicate`."""
    template = _clone(it, InteractionStatus.duplicate.value)
    try:
        async with db.begin_nested():
            if lock_membership_id is not None:
                # trava o membro ANTES do insert: o insert (FK) pega FOR KEY SHARE e dois
                # inserts concorrentes seguidos de FOR UPDATE gerariam deadlock
                await lock_membership(db, lock_membership_id)
            db.add(it)
            if decide is not None:
                await decide(it)
            else:
                await db.flush()
        return PipelineResult("created", it)
    except IntegrityError:
        existing = await _get_existing(db, template.type, template.ig_event_id)
        if existing is not None:
            return PipelineResult("exists", existing)
    # Outro evento ja premiou este comentario (indice unico parcial): vira duplicate.
    try:
        async with db.begin_nested():
            db.add(template)
            await db.flush()
        return PipelineResult("created", template)
    except IntegrityError:
        existing = await _get_existing(db, template.type, template.ig_event_id)
        if existing is None:
            raise
        return PipelineResult("exists", existing)


# ------------------------------------------------------------------ entrada


def _is_transient_ig(exc: InstagramError) -> bool:
    if isinstance(exc, InstagramAuthError):
        return False
    return isinstance(exc, InstagramRateLimitError) or exc.status is None or exc.status >= 500


async def _resolve_story_username(account: InstagramAccount, scoped_id: str) -> str | None:
    """Username do remetente. Falha temporaria repete o job; falha definitiva devolve None
    (a interacao fica unmatched e continua re-casavel por ig_scoped_id)."""
    if account.status != AccountStatus.active.value:
        return None
    try:
        token = decrypt(account.access_token_enc)
        return normalize_username(await get_instagram_client().get_user_username(token, scoped_id))
    except InstagramAuthError:
        account.status = AccountStatus.expired.value
        return None
    except InstagramError as exc:
        if _is_transient_ig(exc):
            raise TransientPipelineError("resolucao do username falhou") from exc
        log.warning("username do story nao resolvido", extra={"event": "story"})
        return None
    except ValueError:
        return None


async def process_event(db: AsyncSession, ev: InboundEvent) -> PipelineResult:
    """Unica porta de entrada para comentarios e mencoes em story. Faz commit.

    Roda em modo SISTEMA mesmo quando chamado de uma rota do gestor (simulador, sync): o
    evento vem da Meta e pode tocar outra organizacao (ex.: verificacao do @)."""
    async with rls.system(db):
        try:
            result = await _process(db, ev)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


async def _process(db: AsyncSession, ev: InboundEvent) -> PipelineResult:
    existing = await _get_existing(db, ev.type, ev.ig_event_id)
    if existing is not None:
        return PipelineResult("exists", existing)
    loaded = await _load_account(db, ev.account_ig_id)
    if loaded is None:
        return PipelineResult("dropped")
    account, org = loaded
    if ev.type == InteractionType.comment.value:
        return await _process_comment(db, ev, account, org)
    if ev.type == InteractionType.story_mention.value:
        return await _process_story(db, ev, account, org)
    return PipelineResult("dropped")


async def _process_comment(
    db: AsyncSession, ev: InboundEvent, account: InstagramAccount, org: Organization
) -> PipelineResult:
    username = normalize_username(ev.from_username)
    code = verification.find_code(ev.text)
    if code is not None:
        # Comentario de verificacao do @ (em qualquer post da conta): prova de posse, nao
        # participacao. Nunca pontua e nao e guardado.
        await verification.confirm_by_comment(db, code, username, ev.from_id)
        return PipelineResult("dropped")
    if ev.parent_id or not ev.media_id:
        return PipelineResult("dropped")
    if (ev.from_id and ev.from_id == account.ig_user_id) or (
        username and username == account.username.lower()
    ):
        return PipelineResult("dropped")  # comentario do proprio gestor
    campaign = await _find_comment_campaign(db, org.id, ev.media_id)
    if campaign is None or campaign.points_comment <= 0:
        return PipelineResult("dropped")
    membership = await _match_membership(db, org.id, ev.from_id, username)
    it = Interaction(
        organization_id=org.id,
        campaign_id=campaign.id,
        membership_id=membership.id if membership else None,
        type=ev.type,
        ig_event_id=ev.ig_event_id,
        ig_username=username,
        ig_scoped_id=ev.from_id,
        text=ev.text,
        occurred_at=ev.occurred_at,
        status=InteractionStatus.unmatched.value,
        points_awarded=0,
    )
    if not _in_window(campaign, ev.occurred_at):
        it.status = InteractionStatus.out_of_window.value
        return await _persist(db, it, None)
    if membership is None:
        return await _persist(db, it, None)

    async def decide(i: Interaction) -> None:
        await _decide_comment(db, i, campaign.id, membership.id)

    return await _persist(db, it, decide, membership.id)


async def _process_story(
    db: AsyncSession, ev: InboundEvent, account: InstagramAccount, org: Organization
) -> PipelineResult:
    if ev.from_id and ev.from_id == account.ig_user_id:
        return PipelineResult("dropped")
    username = normalize_username(ev.from_username)
    if username is None and ev.from_id:
        username = await _resolve_story_username(account, ev.from_id)
    if username and username == account.username.lower():
        return PipelineResult("dropped")
    membership = await _match_membership(db, org.id, ev.from_id, username)
    candidates = await _story_candidates(db, org.id, ev.occurred_at)
    it = Interaction(
        organization_id=org.id,
        campaign_id=candidates[0].id if candidates else None,
        membership_id=membership.id if membership else None,
        type=ev.type,
        ig_event_id=ev.ig_event_id,
        ig_username=username,
        ig_scoped_id=ev.from_id,
        media_url=ev.media_url,
        occurred_at=ev.occurred_at,
        status=InteractionStatus.unmatched.value,
        points_awarded=0,
    )
    if not candidates:
        it.status = InteractionStatus.out_of_window.value
        return await _persist(db, it, None)
    if membership is None:
        return await _persist(db, it, None)

    async def decide(i: Interaction) -> None:
        await _decide_story(db, i, membership.id)

    # trava o membro antes do insert (mesma ordem do caminho de comentarios: sem deadlock)
    return await _persist(db, it, decide, membership.id)


# ------------------------------------------------------------------ re-match


async def rematch_membership(db: AsyncSession, membership_id: uuid.UUID) -> int:
    """Reprocessa interacoes `unmatched` de campanhas ativas para um membro aprovado
    MANUALMENTE pelo gestor, em lotes ate esgotar. Faz commit; devolve quantas viraram awarded.

    So a aprovacao manual dispara o re-match: aprovacao automatica nunca credita retroativamente.
    """
    row = (
        await db.execute(
            select(Membership, PromoterProfile)
            .join(PromoterProfile, PromoterProfile.user_id == Membership.promoter_id)
            .where(
                Membership.id == membership_id,
                Membership.status == "approved",
                Membership.approved_by.is_not(None),
            )
        )
    ).first()
    if row is None:
        return 0
    membership, profile = row
    conds = [Interaction.ig_username == profile.instagram_username]
    if profile.ig_scoped_id:
        conds.append(Interaction.ig_scoped_id == profile.ig_scoped_id)
    awarded = 0
    cursor: tuple[datetime, uuid.UUID] | None = None
    while True:
        stmt = (
            select(Interaction.id, Interaction.occurred_at)
            .join(Campaign, Campaign.id == Interaction.campaign_id)
            .where(
                Interaction.organization_id == membership.organization_id,
                Interaction.status == InteractionStatus.unmatched.value,
                Campaign.status == CampaignStatus.active.value,
                or_(*conds),
            )
            .order_by(Interaction.occurred_at, Interaction.id)
            .limit(REMATCH_BATCH)
        )
        if cursor is not None:
            stmt = stmt.where(
                (Interaction.occurred_at > cursor[0])
                | ((Interaction.occurred_at == cursor[0]) & (Interaction.id > cursor[1]))
            )
        batch = (await db.execute(stmt)).all()
        if not batch:
            break
        for iid, _at in batch:
            try:
                awarded += await _rematch_one(db, iid, membership.id)
                await db.commit()
            except Exception:
                await db.rollback()
                log.exception("rematch falhou", extra={"event": "rematch"})
        cursor = (batch[-1][1], batch[-1][0])
        if len(batch) < REMATCH_BATCH:
            break
    return awarded


async def _rematch_one(
    db: AsyncSession, interaction_id: uuid.UUID, membership_id: uuid.UUID
) -> int:
    it = (
        await db.execute(
            select(Interaction)
            .where(Interaction.id == interaction_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if it is None or it.status != InteractionStatus.unmatched.value or it.campaign_id is None:
        return 0
    try:
        async with db.begin_nested():
            if it.type == InteractionType.comment.value:
                await _decide_comment(db, it, it.campaign_id, membership_id)
            else:
                await _decide_story(db, it, membership_id)
    except IntegrityError:
        it = await db.get(Interaction, interaction_id, populate_existing=True)
        if it is not None and it.status == InteractionStatus.unmatched.value:
            _no_award(it, InteractionStatus.duplicate, membership_id)
            await db.flush()
        return 0
    return 1 if it.status == InteractionStatus.awarded.value else 0


__all__ = [
    "InboundEvent",
    "PipelineResult",
    "TransientPipelineError",
    "normalize_username",
    "process_event",
    "rematch_membership",
]
