"""aprovacao manual, container de publicacao, cursor de sync e unicidade por post

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("memberships", sa.Column("approved_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_memberships_approved_by_users",
        "memberships",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_memberships_approved_by", "memberships", ["approved_by"])
    # Aprovacoes ja existentes foram feitas pelo gestor: preserva o comportamento atual.
    op.execute(
        "UPDATE memberships m SET approved_by = o.owner_id FROM organizations o "
        "WHERE m.organization_id = o.id AND m.status = 'approved'"
    )

    op.add_column("campaigns", sa.Column("publish_container_id", sa.String(64), nullable=True))
    op.add_column(
        "campaigns", sa.Column("publish_container_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("campaigns", sa.Column("sync_cursor", sa.Text(), nullable=True))
    op.add_column(
        "campaigns", sa.Column("sync_full_pass_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "uq_campaigns_org_media_open",
        "campaigns",
        ["organization_id", "ig_media_id"],
        unique=True,
        postgresql_where=sa.text("ig_media_id IS NOT NULL AND status <> 'ended'"),
    )


def downgrade() -> None:
    op.drop_index("uq_campaigns_org_media_open", table_name="campaigns")
    for col in ("sync_full_pass_at", "sync_cursor", "publish_container_at", "publish_container_id"):
        op.drop_column("campaigns", col)
    op.drop_index("ix_memberships_approved_by", table_name="memberships")
    op.drop_constraint("fk_memberships_approved_by_users", "memberships", type_="foreignkey")
    op.drop_column("memberships", "approved_by")
