"""Add account_locked_admin/account_unlocked_admin event types.

Bloqueo y desbloqueo de cuenta hechos DIRECTAMENTE por un administrador
(is_active toggled vía /api/v3/core/users/{id}/), a diferencia de
account_lockout que es por intentos fallidos de login.

Revision ID: 016_add_admin_lock_events
Revises: 015_add_lockout_threshold
Create Date: 2026-07-04
"""
from alembic import op

revision = '016_add_admin_lock_events'
down_revision = '015_add_lockout_threshold'
branch_labels = None
depends_on = None

_OLD_TYPES = "'password_reset','new_account','account_lockout','email_verification','security_change'"
_NEW_TYPES = _OLD_TYPES + ",'account_locked_admin','account_unlocked_admin'"


def upgrade():
    op.drop_constraint('ck_email_bodies_event_type', 'tenant_email_bodies', type_='check')
    op.create_check_constraint(
        'ck_email_bodies_event_type',
        'tenant_email_bodies',
        f"event_type IN ({_NEW_TYPES})",
    )


def downgrade():
    op.drop_constraint('ck_email_bodies_event_type', 'tenant_email_bodies', type_='check')
    op.create_check_constraint(
        'ck_email_bodies_event_type',
        'tenant_email_bodies',
        f"event_type IN ({_OLD_TYPES})",
    )
