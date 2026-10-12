"""LGPD (retencao, exclusao de dados, verificacao do @) e Row Level Security

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- retencao: data de encerramento da campanha
    op.add_column("campaigns", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))
    # campanhas ja encerradas: melhor estimativa e o fim previsto ou a criacao
    op.execute(
        "UPDATE campaigns SET ended_at = COALESCE(ends_at, last_synced_at, created_at) "
        "WHERE status = 'ended'"
    )

    # ---- exclusao de dados pedida pela Meta (so o hash do id do Instagram)
    op.create_table(
        "data_deletion_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("confirmation_code", sa.String(32), nullable=False),
        sa.Column("subject_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("items_removed", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_data_deletion_requests"),
        sa.UniqueConstraint(
            "confirmation_code", name="uq_data_deletion_requests_confirmation_code"
        ),
    )
    op.create_index(
        "ix_data_deletion_requests_subject_hash", "data_deletion_requests", ["subject_hash"]
    )

    # ---- verificacao do @ por codigo em comentario (e disputa: promoter sem @ enquanto prova)
    op.alter_column("promoter_profiles", "instagram_username", nullable=True)
    op.create_table(
        "username_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("instagram_username", sa.String(30), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_username_claims"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_username_claims_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("code", name="uq_username_claims_code"),
    )
    op.create_index(
        "uq_username_claims_open_user",
        "username_claims",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_table("username_claims")
    op.execute("DELETE FROM promoter_profiles WHERE instagram_username IS NULL")
    op.alter_column("promoter_profiles", "instagram_username", nullable=False)
    op.drop_table("data_deletion_requests")
    op.drop_column("campaigns", "ended_at")
