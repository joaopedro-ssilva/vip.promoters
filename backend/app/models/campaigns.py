import uuid
from datetime import datetime

from sqlalchemy import (
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
    Base,
    CampaignSource,
    CampaignStatus,
    InteractionStatus,
    InteractionType,
    check_in,
    utcnow,
)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        check_in("status", CampaignStatus),
        check_in("source", CampaignSource),
        Index("ix_campaigns_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_campaigns_org_media", "organization_id", "ig_media_id"),
        Index("ix_campaigns_status_ends_at", "status", "ends_at"),
        # no maximo uma campanha nao encerrada por post
        Index(
            "uq_campaigns_org_media_open",
            "organization_id",
            "ig_media_id",
            unique=True,
            postgresql_where=text("ig_media_id IS NOT NULL AND status <> 'ended'"),
        ),
        Index("ix_campaigns_org_status_dispatched", "organization_id", "status", "dispatched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=CampaignStatus.draft.value)
    source: Mapped[str] = mapped_column(String(16))
    ig_media_id: Mapped[str | None] = mapped_column(String(64))
    permalink: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[str | None] = mapped_column(String(32))
    media_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    publish_image_url: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    points_comment: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    points_story_mention: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_story_mentions: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # quando a campanha encerrou (manual ou pelo prazo): base da politica de retencao
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publish_container_id: Mapped[str | None] = mapped_column(String(64))
    publish_container_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_cursor: Mapped[str | None] = mapped_column(Text)
    sync_full_pass_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        UniqueConstraint("type", "ig_event_id", name="uq_interactions_type_event"),
        # Ultima linha de defesa: no maximo 1 comentario premiado por campanha/membro.
        Index(
            "uq_interactions_awarded_comment",
            "campaign_id",
            "membership_id",
            unique=True,
            postgresql_where=text("type = 'comment' AND status = 'awarded'"),
        ),
        check_in("type", InteractionType),
        check_in("status", InteractionStatus),
        Index("ix_interactions_campaign_occurred", "campaign_id", "occurred_at"),
        Index("ix_interactions_org_occurred", "organization_id", "occurred_at"),
        Index("ix_interactions_membership", "membership_id"),
        Index("ix_interactions_org_status_username", "organization_id", "status", "ig_username"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    membership_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("memberships.id", ondelete="SET NULL")
    )
    type: Mapped[str] = mapped_column(String(16))
    ig_event_id: Mapped[str] = mapped_column(String(128))
    ig_username: Mapped[str | None] = mapped_column(String(64))
    ig_scoped_id: Mapped[str | None] = mapped_column(String(64))
    text: Mapped[str | None] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    points_awarded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
