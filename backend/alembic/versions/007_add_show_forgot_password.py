"""add show_forgot_password to tenant_themes

Revision ID: 007_add_show_forgot_password
Revises: 006_add_access_and_notifications
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = '007_add_show_forgot_password'
down_revision = '006_add_access_and_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tenant_themes',
        sa.Column(
            'show_forgot_password',
            sa.Boolean(),
            server_default='true',
            nullable=False,
        )
    )


def downgrade() -> None:
    op.drop_column('tenant_themes', 'show_forgot_password')
