from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    manager = "manager"
    promoter = "promoter"


class MembershipStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    removed = "removed"


class CampaignStatus(StrEnum):
    draft = "draft"
    active = "active"
    ended = "ended"


class CampaignSource(StrEnum):
    existing = "existing"
    publish = "publish"


class InteractionType(StrEnum):
    comment = "comment"
    story_mention = "story_mention"


class InteractionStatus(StrEnum):
    awarded = "awarded"
    duplicate = "duplicate"
    unmatched = "unmatched"
    out_of_window = "out_of_window"


class TxType(StrEnum):
    earn = "earn"
    redeem = "redeem"
    refund = "refund"
    adjust = "adjust"


class RedemptionStatus(StrEnum):
    pending = "pending"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class AccountStatus(StrEnum):
    active = "active"
    expired = "expired"
    revoked = "revoked"


def check_in(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    values = ", ".join(f"'{e.value}'" for e in enum)
    return CheckConstraint(f"{column} in ({values})", name=name or column)
