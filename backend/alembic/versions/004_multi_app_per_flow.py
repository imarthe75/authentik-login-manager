"""004_multi_app_per_flow: allow multiple app themes per flow slug

Revision ID: 004_multi_app_per_flow
Revises: 003_add_container_colors
Create Date: 2026-05-31
"""
from alembic import op

revision: str = '004_multi_app_per_flow'
down_revision: str = '003_add_container_colors'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the individual unique constraint on flow_slug
    op.drop_index('ix_tenant_themes_authentik_flow_slug', table_name='tenant_themes')

    # Re-add as non-unique index (for query performance)
    op.create_index('ix_tenant_themes_authentik_flow_slug', 'tenant_themes', ['authentik_flow_slug'], unique=False)

    # Unique: at most one global theme per flow (app_slug IS NULL)
    op.create_index(
        'uq_theme_flow_global',
        'tenant_themes',
        ['authentik_flow_slug'],
        unique=True,
        postgresql_where="authentik_app_slug IS NULL",
    )

    # Unique: at most one theme per (flow, app) pair
    op.create_index(
        'uq_theme_flow_app',
        'tenant_themes',
        ['authentik_flow_slug', 'authentik_app_slug'],
        unique=True,
        postgresql_where="authentik_app_slug IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index('uq_theme_flow_app', table_name='tenant_themes')
    op.drop_index('uq_theme_flow_global', table_name='tenant_themes')
    op.drop_index('ix_tenant_themes_authentik_flow_slug', table_name='tenant_themes')
    op.create_index('ix_tenant_themes_authentik_flow_slug', 'tenant_themes', ['authentik_flow_slug'], unique=True)
