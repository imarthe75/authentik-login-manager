"""Add logo_top_text_color, logo_top_text_size, logo_bottom_text_color, logo_bottom_text_size columns

Revision ID: 020_add_logo_text_styling
Revises: 019_add_title_subtitle_colors
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = '020_add_logo_text_styling'
down_revision = '019_add_title_subtitle_colors'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('tenant_themes', sa.Column('logo_top_text_color', sa.String(length=7), server_default='#FFFFFF', nullable=False))
    op.add_column('tenant_themes', sa.Column('logo_top_text_size', sa.Integer(), server_default='24', nullable=False))
    op.add_column('tenant_themes', sa.Column('logo_bottom_text_color', sa.String(length=7), server_default='#FFFFFF', nullable=False))
    op.add_column('tenant_themes', sa.Column('logo_bottom_text_size', sa.Integer(), server_default='20', nullable=False))

def downgrade():
    op.drop_column('tenant_themes', 'logo_bottom_text_size')
    op.drop_column('tenant_themes', 'logo_bottom_text_color')
    op.drop_column('tenant_themes', 'logo_top_text_size')
    op.drop_column('tenant_themes', 'logo_top_text_color')
