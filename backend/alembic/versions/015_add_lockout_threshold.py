"""Add lockout_failed_attempts to password_policies.

Cuántos intentos fallidos de login se permiten antes de bloquear la cuenta —
sincronizado con el threshold real de la ReputationPolicy 'casmarts-lockout-reputation'
en Authentik (threshold = -lockout_failed_attempts, ya que cada login_failed resta
1 punto de reputación — ver authentik/policies/reputation/signals.py). Default 5
coincide con el valor -5 sembrado por el blueprint casmarts-event-webhooks.yaml.

Revision ID: 015_add_lockout_threshold
Revises: 014_add_link_expiry
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = '015_add_lockout_threshold'
down_revision = '014_add_link_expiry'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('password_policies', sa.Column('lockout_failed_attempts', sa.Integer(), nullable=False, server_default='5'))


def downgrade():
    op.drop_column('password_policies', 'lockout_failed_attempts')
