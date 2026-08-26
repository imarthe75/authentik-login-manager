"""Add system_name_color and system_subtitle_color columns

Revision ID: 019_add_title_subtitle_colors
Revises: 018_add_expansion_config
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = '019_add_title_subtitle_colors'
down_revision = '018_add_expansion_config'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('tenant_themes', sa.Column('system_name_color', sa.String(length=7), server_default='#111827', nullable=False))
    op.add_column('tenant_themes', sa.Column('system_subtitle_color', sa.String(length=7), server_default='#374151', nullable=False))

def downgrade():
    op.drop_column('tenant_themes', 'system_subtitle_color')
    op.drop_column('tenant_themes', 'system_name_color')
