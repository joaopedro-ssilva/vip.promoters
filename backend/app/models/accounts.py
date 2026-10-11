import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    AccountStatus,
    Base,
    MembershipStatus,
    Role,
    check_in,
    utcnow,
)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        check_in("role", Role),
        CheckConstraint("email = lower(email)", name="email_lower"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = _created()


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    user_agent: Mapped[str | None] = mapped_column(String(255))


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(120))
    invite_code: Mapped[str] = mapped_column(String(16), unique=True)
    auto_approve_promoters: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = _created()


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"
    __table_args__ = (check_in("status", AccountStatus),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    ig_user_id: Mapped[str] = mapped_column(String(64), unique=True)
    username: Mapped[str] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(160))
    profile_picture_url: Mapped[str | None] = mapped_column(Text)
    account_type: Mapped[str | None] = mapped_column(String(32))
    followers_count: Mapped[int | None] = mapped_column(Integer)
    access_token_enc: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default=text("'{}'")
    )
    webhook_subscribed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(16), default=AccountStatus.active.value, server_default="active"
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )


class PromoterProfile(Base):
    __tablename__ = "promoter_profiles"
    __table_args__ = (
        CheckConstraint("instagram_username = lower(instagram_username)", name="username_lower"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    instagram_username: Mapped[str] = mapped_column(String(30), unique=True)
    ig_scoped_id: Mapped[str | None] = mapped_column(String(64), index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_method: Mapped[str | None] = mapped_column(String(16))


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "promoter_id", name="uq_memberships_org_promoter"),
        CheckConstraint("points_balance >= 0", name="points_balance_nonneg"),
        CheckConstraint("total_earned >= 0", name="total_earned_nonneg"),
        check_in("status", MembershipStatus),
        Index("ix_memberships_org_status", "organization_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    promoter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default=MembershipStatus.pending.value)
    points_balance: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_earned: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # preenchido so na aprovacao MANUAL do gestor (prova de identidade do @)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


__all__ = [
    "InstagramAccount",
    "Membership",
    "Organization",
    "PromoterProfile",
    "RefreshToken",
    "User",
]
