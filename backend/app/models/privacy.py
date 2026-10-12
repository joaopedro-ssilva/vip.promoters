import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class DataDeletionRequest(Base):
    """Pedido de exclusao de dados recebido da Meta (callback de data deletion).

    Guarda so o HASH do id do Instagram: o registro prova que o pedido foi atendido sem
    manter o identificador que se pediu para apagar."""

    __tablename__ = "data_deletion_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    confirmation_code: Mapped[str] = mapped_column(String(32), unique=True)
    subject_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    items_removed: Mapped[int] = mapped_column(default=0, server_default="0")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsernameClaim(Base):
    """Verificacao de posse de um @ do Instagram por codigo em comentario.

    O promoter recebe um codigo (VIP-XXXXXX) e comenta em qualquer post de uma conta
    conectada ao app. O webhook entrega o comentario com o @ AUTENTICO de quem comentou
    (vem da Meta, nao do usuario): se bater com o @ pedido, o promoter prova que controla
    a conta. Serve para o selo "@ verificado" e para RECLAMAR um @ que outra pessoa cadastrou
    sem verificar (disputa)."""

    __tablename__ = "username_claims"
    __table_args__ = (
        Index(
            "uq_username_claims_open_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    instagram_username: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(16), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|verified|expired
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
