"""add container colors

Revision ID: 003_add_container_colors
Revises: 002_add_app_slug
Create Date: 2026-05-29T14:00:00Z

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '003_add_container_colors'
down_revision: Union[str, None] = '002_add_app_slug'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tenant_themes',
        sa.Column('card_bg_color', sa.String(length=7), nullable=False, server_default='#FFFFFF')
    )
    op.add_column(
        'tenant_themes',
        sa.Column('panel_bg_color', sa.String(length=7), nullable=False, server_default='#F6F9FD')
    )


def downgrade() -> None:
    op.drop_column('tenant_themes', 'panel_bg_color')
    op.drop_column('tenant_themes', 'card_bg_color')
