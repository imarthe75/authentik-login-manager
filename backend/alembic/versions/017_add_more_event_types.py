"""Add remaining user-facing Authentik event types.

login_success, suspicious_request, invitation_used, app_authorized,
impersonation_started, account_deleted — el resto de los ~30 EventAction de
Authentik son puramente internos/operativos (system_exception,
policy_exception, flow_execution, etc.) y no tienen sentido como correo a un
usuario final; quedan fuera a propósito. impersonation_ended también queda
fuera: Authentik no deja ninguna referencia a qué usuario fue impersonado en
ese evento (ver authentik_events.py).

Revision ID: 017_add_more_event_types
Revises: 016_add_admin_lock_events
Create Date: 2026-07-04
"""
from alembic import op

revision = '017_add_more_event_types'
down_revision = '016_add_admin_lock_events'
branch_labels = None
depends_on = None

_OLD_TYPES = (
    "'password_reset','new_account','account_lockout','email_verification',"
    "'security_change','account_locked_admin','account_unlocked_admin'"
)
_NEW_TYPES = _OLD_TYPES + (
    ",'login_success','suspicious_request','invitation_used','app_authorized',"
    "'impersonation_started','account_deleted'"
)


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
