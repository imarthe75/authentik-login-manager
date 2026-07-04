"""Add hibp_allowed_count and password expiry fields to password_policies.

hibp_allowed_count mirrors Authentik's live default (0 — reject on any
breach match, the strictest setting) so the first GET matches reality.
expiry_enabled/expiry_days model a SEPARATE Authentik policy type
(authentik_policies_expiry.PasswordExpiryPolicy) that today has zero
instances configured — expiry_enabled defaults to false to match that.

Revision ID: 013_add_password_expiry
Revises: 012_add_password_policy
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = '013_add_password_expiry'
down_revision = '012_add_password_policy'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('password_policies', sa.Column('hibp_allowed_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('password_policies', sa.Column('expiry_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('password_policies', sa.Column('expiry_days', sa.Integer(), nullable=False, server_default='90'))


def downgrade():
    op.drop_column('password_policies', 'expiry_days')
    op.drop_column('password_policies', 'expiry_enabled')
    op.drop_column('password_policies', 'hibp_allowed_count')
