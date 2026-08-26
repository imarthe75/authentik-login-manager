"""Add font_heading/font_body columns + custom font upload slots

Revision ID: 023_add_theme_fonts
Revises: 022_add_tenant_applications
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = '023_add_theme_fonts'
down_revision = '022_add_tenant_applications'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenant_themes', sa.Column('font_heading', sa.String(length=30), server_default='inter', nullable=False))
    op.add_column('tenant_themes', sa.Column('font_body', sa.String(length=30), server_default='inter', nullable=False))
    op.add_column('tenant_themes', sa.Column('custom_font_heading_base64', sa.Text(), nullable=True))
    op.add_column('tenant_themes', sa.Column('custom_font_heading_name', sa.String(length=100), nullable=True))
    op.add_column('tenant_themes', sa.Column('custom_font_body_base64', sa.Text(), nullable=True))
    op.add_column('tenant_themes', sa.Column('custom_font_body_name', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('tenant_themes', 'custom_font_body_name')
    op.drop_column('tenant_themes', 'custom_font_body_base64')
    op.drop_column('tenant_themes', 'custom_font_heading_name')
    op.drop_column('tenant_themes', 'custom_font_heading_base64')
    op.drop_column('tenant_themes', 'font_body')
    op.drop_column('tenant_themes', 'font_heading')
