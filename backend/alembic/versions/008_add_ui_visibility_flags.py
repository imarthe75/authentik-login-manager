"""Add UI visibility flags (logos panel, password toggle, system name/subtitle, field labels)

Revision ID: 008_add_ui_visibility_flags
Revises: 007_add_show_forgot_password
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = '008_add_ui_visibility_flags'
down_revision = '007_add_show_forgot_password'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenant_themes', sa.Column('show_logos_panel', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('tenant_themes', sa.Column('show_password_toggle', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('tenant_themes', sa.Column('show_system_name', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('tenant_themes', sa.Column('show_system_subtitle', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('tenant_themes', sa.Column('show_field_labels', sa.Boolean(), server_default='true', nullable=False))


def downgrade():
    op.drop_column('tenant_themes', 'show_field_labels')
    op.drop_column('tenant_themes', 'show_system_subtitle')
    op.drop_column('tenant_themes', 'show_system_name')
    op.drop_column('tenant_themes', 'show_password_toggle')
    op.drop_column('tenant_themes', 'show_logos_panel')
