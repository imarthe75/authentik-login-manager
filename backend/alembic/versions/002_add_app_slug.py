"""add authentik_app_slug column

Revision ID: 002_add_app_slug
Revises: 001_initial_schema
Create Date: 2026-05-29T13:00:00Z

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_app_slug'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tenant_themes',
        sa.Column('authentik_app_slug', sa.String(length=100), nullable=True)
    )
    op.create_index(
        op.f('ix_tenant_themes_authentik_app_slug'), 
        'tenant_themes', 
        ['authentik_app_slug'], 
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_tenant_themes_authentik_app_slug'), table_name='tenant_themes')
    op.drop_column('tenant_themes', 'authentik_app_slug')
