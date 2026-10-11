import uuid
from datetime import datetime

from sqlalchemy import (
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

from app.models.base import Base, RedemptionStatus, TxType, check_in, utcnow


class Reward(Base):
    __tablename__ = "rewards"
    __table_args__ = (
        CheckConstraint("cost_points > 0", name="cost_positive"),
        CheckConstraint("stock IS NULL OR stock >= 0", name="stock_nonneg"),
        CheckConstraint("max_per_promoter IS NULL OR max_per_promoter > 0", name="max_positive"),
        Index("ix_rewards_org_active", "organization_id", "is_active", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    cost_points: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int | None] = mapped_column(Integer)
    max_per_promoter: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )


class Redemption(Base):
    __tablename__ = "redemptions"
    __table_args__ = (
        UniqueConstraint("membership_id", "request_id", name="uq_redemptions_membership_request"),
        check_in("status", RedemptionStatus),
        Index("ix_redemptions_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_redemptions_membership_created", "membership_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    reward_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rewards.id", ondelete="RESTRICT"), index=True
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE")
    )
    request_id: Mapped[uuid.UUID] = mapped_column()
    cost_points: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default=RedemptionStatus.pending.value)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class PointTransaction(Base):
    __tablename__ = "point_transactions"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="amount_nonzero"),
        CheckConstraint("balance_after >= 0", name="balance_after_nonneg"),
        check_in("type", TxType),
        Index("ix_point_tx_membership_created", "membership_id", "created_at"),
        Index("ix_point_tx_org_created", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE")
    )
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(255))
    balance_after: Mapped[int] = mapped_column(Integer)
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interactions.id", ondelete="SET NULL"), index=True
    )
    redemption_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("redemptions.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index(
            "ix_notifications_user_unread",
            "user_id",
            postgresql_where=text("read_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(255))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
