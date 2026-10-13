"""LGPD (retencao, exclusao de dados, verificacao do @) e Row Level Security

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

# Tabelas com organization_id: so mostram as organizacoes do contexto (app/core/rls.py).
TENANT_TABLES = (
    "memberships",
    "campaigns",
    "interactions",
    "rewards",
    "redemptions",
    "point_transactions",
)

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


    # ---- Row Level Security (segunda camada do isolamento entre organizacoes)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_rls_system() RETURNS boolean
        LANGUAGE sql STABLE AS $$
            SELECT coalesce(current_setting('app.rls_mode', true), '') = 'system'
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_org_ids() RETURNS uuid[]
        LANGUAGE sql STABLE AS $$
            SELECT coalesce(
                string_to_array(nullif(current_setting('app.org_ids', true), ''), ',')::uuid[],
                '{}'::uuid[]
            )
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_user_id() RETURNS uuid
        LANGUAGE sql STABLE AS $$
            SELECT nullif(current_setting('app.user_id', true), '')::uuid
        $$
        """
    )
    for table in TENANT_TABLES:
        extra = " OR promoter_id = app_user_id()" if table == "memberships" else ""
        cond = f"app_rls_system() OR organization_id = ANY (app_org_ids()){extra}"
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant ON {table} USING ({cond}) WITH CHECK ({cond})")
    org_cond = "app_rls_system() OR id = ANY (app_org_ids()) OR owner_id = app_user_id()"
    op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant ON organizations USING ({org_cond}) WITH CHECK ({org_cond})")
    # Conta do Instagram (guarda o token cifrado): a propria, ou a do dono de uma equipe
    # visivel (o promoter ve o @ da equipe na lista de participacoes).
    ig_cond = (
        "app_rls_system() OR user_id = app_user_id() OR user_id IN "
        "(SELECT owner_id FROM organizations WHERE id = ANY (app_org_ids()))"
    )
    op.execute("ALTER TABLE instagram_accounts ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant ON instagram_accounts USING ({ig_cond}) WITH CHECK ({ig_cond})"
    )


def downgrade() -> None:
    for table in (*TENANT_TABLES, "organizations", "instagram_accounts"):
        op.execute(f"DROP POLICY IF EXISTS tenant ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION IF EXISTS app_rls_system(), app_org_ids(), app_user_id()")
    op.drop_table("username_claims")
    op.execute("DELETE FROM promoter_profiles WHERE instagram_username IS NULL")
    op.alter_column("promoter_profiles", "instagram_username", nullable=False)
    op.drop_table("data_deletion_requests")
    op.drop_column("campaigns", "ended_at")
