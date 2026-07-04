"""Add link_expiry_minutes to password_policies.

Controls how long the one-time password-setup/recovery link is valid —
synced to the live 'casmarts-smtp-gmail' EmailStage's token_expiry field
(shared by both password_reset and new_account, since both redirect through
the same password-recovery flow). Default 60 matches the current live value.

Revision ID: 014_add_link_expiry
Revises: 013_add_password_expiry
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = '014_add_link_expiry'
down_revision = '013_add_password_expiry'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('password_policies', sa.Column('link_expiry_minutes', sa.Integer(), nullable=False, server_default='60'))


def downgrade():
    op.drop_column('password_policies', 'link_expiry_minutes')
