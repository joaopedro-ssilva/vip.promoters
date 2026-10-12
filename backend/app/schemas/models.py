"""Schemas de entrada e saida (contrato em docs/ARCHITECTURE.md, secao 8)."""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.schemas.common import (
    Email,
    IGUsername,
    ImageUrl,
    InviteCode,
    LoginPassword,
    Password,
    PersonName,
)


def _aware(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        return v.replace(tzinfo=UTC)
    return v


AwareDT = Annotated[datetime, AfterValidator(_aware)]  # type: ignore[arg-type]
Trimmed = Annotated[str, StringConstraints(strip_whitespace=True)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="ignore")


# =============================================================== entrada


class RegisterIn(Strict):
    name: PersonName
    email: Email
    password: Password
    role: Literal["manager", "promoter"]
    organization_name: PersonName | None = None
    instagram_username: IGUsername | None = None
    invite_code: InviteCode | None = None
    # O @ ja foi cadastrado por outra pessoa sem verificacao e quem se cadastra diz que e
    # dono: a conta nasce sem @ e com um pedido de verificacao (disputa).
    claim_username: bool = False


class LoginIn(Strict):
    email: Email
    password: LoginPassword


class PatchMeIn(Strict):
    name: PersonName


class ChangePasswordIn(Strict):
    current_password: LoginPassword
    new_password: Password


class DeleteAccountIn(Strict):
    password: LoginPassword
    # o usuario digita EXCLUIR: evita exclusao por clique acidental
    confirmation: Annotated[str, StringConstraints(max_length=20)]


class OrganizationPatchIn(Strict):
    name: PersonName | None = None
    auto_approve_promoters: bool | None = None


class AdjustPointsIn(Strict):
    amount: int = Field(ge=-1_000_000, le=1_000_000)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]

    @field_validator("amount")
    @classmethod
    def _nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("O valor do ajuste não pode ser zero.")
        return v


class CampaignCreateIn(Strict):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None
    ) = None
    instructions: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None
    ) = None
    source: Literal["existing", "publish"]
    ig_media_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] | None = (
        None
    )
    image_url: ImageUrl | None = None
    caption: Annotated[str, StringConstraints(max_length=2200)] | None = None
    starts_at: AwareDT | None = None
    ends_at: AwareDT | None = None
    points_comment: int = Field(10, ge=0, le=100000)
    points_story_mention: int = Field(25, ge=0, le=100000)
    max_story_mentions: int = Field(1, ge=1, le=10)
    dispatch: bool = False

    @field_validator("points_story_mention")
    @classmethod
    def _one_positive(cls, v: int, info: ValidationInfo) -> int:
        if v == 0 and info.data.get("points_comment", 0) == 0:
            raise ValueError("Defina pontos para ao menos uma ação (comentário ou menção).")
        return v

    @field_validator("ends_at")
    @classmethod
    def _after_start(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        start = info.data.get("starts_at")
        if v is not None and start is not None and v <= start:
            raise ValueError("O término deve ser depois do início.")
        return v


class CampaignPatchIn(Strict):
    title: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
        | None
    ) = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None
    ) = None
    instructions: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None
    ) = None
    ends_at: AwareDT | None = None
    points_comment: int | None = Field(None, ge=0, le=100000)
    points_story_mention: int | None = Field(None, ge=0, le=100000)
    max_story_mentions: int | None = Field(None, ge=1, le=10)


class RewardCreateIn(Strict):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None
    ) = None
    image_url: ImageUrl | None = None
    cost_points: int = Field(ge=1, le=1_000_000)
    stock: int | None = Field(None, ge=0, le=100000)
    max_per_promoter: int | None = Field(None, ge=1, le=1000)
    is_active: bool = True


class RewardPatchIn(Strict):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
        | None
    ) = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None
    ) = None
    image_url: ImageUrl | None = None
    cost_points: int | None = Field(None, ge=1, le=1_000_000)
    stock: int | None = Field(None, ge=0, le=100000)
    max_per_promoter: int | None = Field(None, ge=1, le=1000)
    is_active: bool | None = None


class NoteIn(Strict):
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class JoinIn(Strict):
    invite_code: InviteCode


class ProfilePatchIn(Strict):
    instagram_username: IGUsername


class RedeemIn(Strict):
    request_id: uuid.UUID


class SimulateCommentIn(Strict):
    campaign_id: uuid.UUID
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    text: Annotated[str, StringConstraints(max_length=2200)] = "Quero participar!"


class SimulateStoryIn(Strict):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


# =============================================================== saida


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OrganizationOut(Out):
    id: uuid.UUID
    name: str
    invite_code: str
    auto_approve_promoters: bool
    instagram_username: str | None = None
    instagram_profile_picture_url: str | None = None


class OrganizationPreviewOut(Out):
    id: uuid.UUID
    name: str
    instagram_username: str | None = None
    instagram_profile_picture_url: str | None = None
    promoters_count: int


class PromoterProfileOut(Out):
    instagram_username: str | None
    verified: bool
    verification_method: str | None = None


class ClaimIn(Strict):
    instagram_username: IGUsername


class VerificationOut(Out):
    instagram_username: str | None
    verified: bool
    # pedido aberto: comentar `code` em qualquer post de uma conta conectada ao app
    claim_username: str | None = None
    code: str | None = None
    expires_at: datetime | None = None


class UserOut(Out):
    id: uuid.UUID
    name: str
    email: str
    role: str
    created_at: datetime
    organization: OrganizationOut | None = None
    promoter_profile: PromoterProfileOut | None = None


class UserEnvelope(Out):
    user: UserOut


class InstagramAccountOut(Out):
    ig_user_id: str
    username: str
    name: str | None = None
    profile_picture_url: str | None = None
    account_type: str | None = None
    followers_count: int | None = None
    status: str
    token_expires_at: datetime | None = None
    webhook_subscribed: bool
    connected_at: datetime
    scopes: list[str] = []


class InstagramAccountEnvelope(Out):
    account: InstagramAccountOut | None


class AuthorizeUrlOut(Out):
    authorize_url: str


class InstagramMediaOut(Out):
    id: str
    caption: str | None = None
    media_type: str | None = None
    media_product_type: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    permalink: str | None = None
    timestamp: datetime | None = None
    like_count: int | None = None
    comments_count: int | None = None


class MediaListOut(Out):
    items: list[InstagramMediaOut]
    next_cursor: str | None = None


class InviteOut(Out):
    invite_code: str
    invite_url: str


class MemberPromoterOut(Out):
    id: uuid.UUID
    name: str
    email: str
    instagram_username: str | None = None
    verified: bool = False


class MemberOut(Out):
    id: uuid.UUID
    status: str
    points_balance: int
    total_earned: int
    joined_at: datetime
    approved_at: datetime | None = None
    promoter: MemberPromoterOut


class MembershipOut(Out):
    id: uuid.UUID
    status: str
    points_balance: int
    total_earned: int
    joined_at: datetime
    organization: OrganizationPreviewOut


class MembershipListOut(Out):
    items: list[MembershipOut]


class LeaderboardEntryOut(Out):
    rank: int
    membership_id: uuid.UUID
    name: str
    instagram_username: str | None = None
    points: int


class LeaderboardOut(Out):
    items: list[LeaderboardEntryOut]


class MyRankOut(Out):
    rank: int
    points: int


class PromoterLeaderboardOut(Out):
    items: list[LeaderboardEntryOut]
    me: MyRankOut


class CampaignStatsOut(Out):
    comments_awarded: int = 0
    story_mentions_awarded: int = 0
    participants: int = 0
    points_issued: int = 0
    unmatched: int = 0


class CampaignOut(Out):
    id: uuid.UUID
    title: str
    description: str | None = None
    instructions: str | None = None
    status: str
    source: str
    ig_media_id: str | None = None
    permalink: str | None = None
    media_type: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    caption: str | None = None
    publish_image_url: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    points_comment: int
    points_story_mention: int
    max_story_mentions: int
    dispatched_at: datetime | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    stats: CampaignStatsOut


class SyncOut(Out):
    fetched: int
    new_interactions: int
    awarded: int


class InteractionPromoterOut(Out):
    membership_id: uuid.UUID
    name: str


class InteractionOut(Out):
    id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    type: str
    status: str
    ig_username: str | None = None
    text: str | None = None
    media_url: str | None = None
    occurred_at: datetime
    points_awarded: int
    promoter: InteractionPromoterOut | None = None


class InteractionEnvelope(Out):
    interaction: InteractionOut


class PromoterMyOut(Out):
    comment_done: bool
    story_mentions_done: int
    points_earned: int


class PromoterCampaignOut(Out):
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str | None = None
    instructions: str | None = None
    status: str
    permalink: str | None = None
    media_type: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    caption: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    points_comment: int
    points_story_mention: int
    max_story_mentions: int
    my: PromoterMyOut


class PromoterCampaignDetailOut(PromoterCampaignOut):
    my_interactions: list[InteractionOut]


class RewardOut(Out):
    id: uuid.UUID
    name: str
    description: str | None = None
    image_url: str | None = None
    cost_points: int
    stock: int | None = None
    max_per_promoter: int | None = None
    is_active: bool
    redeemed_count: int = 0
    created_at: datetime


class PromoterRewardOut(RewardOut):
    can_afford: bool
    my_redemptions_count: int
    available: bool


class RedemptionRewardOut(Out):
    id: uuid.UUID
    name: str
    image_url: str | None = None


class RedemptionPromoterOut(Out):
    membership_id: uuid.UUID
    name: str
    instagram_username: str | None = None


class RedemptionOut(Out):
    id: uuid.UUID
    code: str
    status: str
    cost_points: int
    note: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    reward: RedemptionRewardOut
    promoter: RedemptionPromoterOut | None = None
    organization_name: str | None = None


class TransactionOut(Out):
    id: uuid.UUID
    amount: int
    type: str
    description: str
    balance_after: int
    created_at: datetime


class NotificationOut(Out):
    id: uuid.UUID
    type: str
    title: str
    body: str
    link: str | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListOut(Out):
    items: list[NotificationOut]
    unread_count: int


class ByDayOut(Out):
    date: str
    comments: int
    story_mentions: int


class DashboardKpisOut(Out):
    promoters_approved: int
    promoters_pending: int
    campaigns_active: int
    interactions_7d: int
    points_issued_30d: int
    redemptions_pending: int


class ManagerDashboardOut(Out):
    instagram_connected: bool
    kpis: DashboardKpisOut
    interactions_by_day: list[ByDayOut]
    top_promoters: list[LeaderboardEntryOut]
    recent_interactions: list[InteractionOut]


class PromoterHomeOut(Out):
    membership: MembershipOut
    rank: int
    promoters_count: int
    active_campaigns: list[PromoterCampaignOut]
    recent_transactions: list[TransactionOut]
    affordable_rewards_count: int


class UploadOut(Out):
    url: str


class ConfigOut(Out):
    app_name: str
    mock_mode: bool
