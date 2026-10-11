"""Montagem das respostas (joins e consultas agregadas; sem N+1)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
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
from app.schemas.models import (
    InteractionOut,
    InteractionPromoterOut,
    MembershipOut,
    OrganizationOut,
    OrganizationPreviewOut,
    PromoterProfileOut,
    RedemptionOut,
    RedemptionPromoterOut,
    RedemptionRewardOut,
    RewardOut,
    UserOut,
)

# ------------------------------------------------------------------ usuario


async def organization_out(db: AsyncSession, org: Organization) -> OrganizationOut:
    row = (
        await db.execute(
            select(InstagramAccount.username, InstagramAccount.profile_picture_url).where(
                InstagramAccount.user_id == org.owner_id
            )
        )
    ).first()
    return OrganizationOut(
        id=org.id,
        name=org.name,
        invite_code=org.invite_code,
        auto_approve_promoters=org.auto_approve_promoters,
        instagram_username=row[0] if row else None,
        instagram_profile_picture_url=row[1] if row else None,
    )


async def user_out(db: AsyncSession, user: User) -> UserOut:
    org_out = None
    profile_out = None
    if user.role == "manager":
        org = (
            await db.execute(select(Organization).where(Organization.owner_id == user.id))
        ).scalar_one_or_none()
        if org is not None:
            org_out = await organization_out(db, org)
    else:
        profile = await db.get(PromoterProfile, user.id)
        if profile is not None:
            profile_out = PromoterProfileOut(
                instagram_username=profile.instagram_username,
                verified=profile.verified,
                verification_method=profile.verification_method,
            )
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        organization=org_out,
        promoter_profile=profile_out,
    )


# ------------------------------------------------------------------ equipes


def membership_preview_query(where) -> Select:
    """Membro + organizacao + @ do Instagram da org + contagem de promoters aprovados."""
    m2 = Membership.__table__.alias("m2")
    approved = (
        select(func.count())
        .select_from(m2)
        .where(m2.c.organization_id == Organization.id, m2.c.status == "approved")
        .correlate(Organization)
        .scalar_subquery()
    )
    return (
        select(
            Membership,
            Organization,
            InstagramAccount.username,
            InstagramAccount.profile_picture_url,
            approved.label("promoters_count"),
        )
        .join(Organization, Organization.id == Membership.organization_id)
        .outerjoin(InstagramAccount, InstagramAccount.user_id == Organization.owner_id)
        .where(where)
    )


def membership_out(row) -> MembershipOut:
    m, org, ig_username, ig_picture, count = row
    return MembershipOut(
        id=m.id,
        status=m.status,
        points_balance=m.points_balance,
        total_earned=m.total_earned,
        joined_at=m.joined_at,
        organization=OrganizationPreviewOut(
            id=org.id,
            name=org.name,
            instagram_username=ig_username,
            instagram_profile_picture_url=ig_picture,
            promoters_count=count or 0,
        ),
    )


# ------------------------------------------------------------------ interacoes


def interaction_query() -> Select:
    return (
        select(Interaction, User.name, Membership.id)
        .outerjoin(Membership, Membership.id == Interaction.membership_id)
        .outerjoin(User, User.id == Membership.promoter_id)
    )


def interaction_out(row) -> InteractionOut:
    it, name, membership_id = row
    return InteractionOut(
        id=it.id,
        campaign_id=it.campaign_id,
        type=it.type,
        status=it.status,
        ig_username=it.ig_username,
        text=it.text,
        media_url=it.media_url,
        occurred_at=it.occurred_at,
        points_awarded=it.points_awarded,
        promoter=(
            InteractionPromoterOut(membership_id=membership_id, name=name)
            if membership_id is not None and name is not None
            else None
        ),
    )


async def load_interaction(db: AsyncSession, interaction_id: uuid.UUID) -> InteractionOut:
    row = (await db.execute(interaction_query().where(Interaction.id == interaction_id))).one()
    return interaction_out(row)


# ------------------------------------------------------------------ recompensas


async def redeemed_counts(
    db: AsyncSession, reward_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not reward_ids:
        return {}
    res = await db.execute(
        select(Redemption.reward_id, func.count())
        .where(
            Redemption.reward_id.in_(reward_ids),
            Redemption.status != RedemptionStatus.cancelled.value,
        )
        .group_by(Redemption.reward_id)
    )
    return dict(res.all())


def reward_out(r: Reward, redeemed: int) -> RewardOut:
    return RewardOut(
        id=r.id,
        name=r.name,
        description=r.description,
        image_url=r.image_url,
        cost_points=r.cost_points,
        stock=r.stock,
        max_per_promoter=r.max_per_promoter,
        is_active=r.is_active,
        redeemed_count=redeemed,
        created_at=r.created_at,
    )


def redemption_query() -> Select:
    return (
        select(
            Redemption,
            Reward.name,
            Reward.image_url,
            User.name,
            PromoterProfile.instagram_username,
            Organization.name,
        )
        .join(Reward, Reward.id == Redemption.reward_id)
        .join(Membership, Membership.id == Redemption.membership_id)
        .join(User, User.id == Membership.promoter_id)
        .outerjoin(PromoterProfile, PromoterProfile.user_id == Membership.promoter_id)
        .join(Organization, Organization.id == Redemption.organization_id)
    )


def redemption_out(row, *, manager_view: bool) -> RedemptionOut:
    r, reward_name, reward_image, promoter_name, username, org_name = row
    return RedemptionOut(
        id=r.id,
        code=r.code,
        status=r.status,
        cost_points=r.cost_points,
        note=r.note,
        created_at=r.created_at,
        resolved_at=r.resolved_at,
        reward=RedemptionRewardOut(id=r.reward_id, name=reward_name, image_url=reward_image),
        promoter=(
            RedemptionPromoterOut(
                membership_id=r.membership_id, name=promoter_name, instagram_username=username
            )
            if manager_view
            else None
        ),
        organization_name=None if manager_view else org_name,
    )


async def load_redemption(
    db: AsyncSession, redemption_id: uuid.UUID, *, manager_view: bool
) -> RedemptionOut:
    row = (await db.execute(redemption_query().where(Redemption.id == redemption_id))).one()
    return redemption_out(row, manager_view=manager_view)
