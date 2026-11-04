"""Convert created_at/updated_at/last_synced_at from timestamp to timestamptz

Revision ID: 025_timestamptz_conversion
Revises: 024_add_audit_columns
Create Date: 2026-11-04

postgres/rules.md #2: "timestamptz, prohibido timestamp sin zona"
(SQL-TIMESTAMP-WITHOUT-TIMEZONE). La base esta en TimeZone=UTC (confirmado
con `SHOW timezone`), asi que la conversion con `AT TIME ZONE 'UTC'` es
exacta y sin perdida — no hay cambio de hora, solo se adjunta la zona que
los valores ya tenian implicita. Ambiente test/QA (autorizado 2026-11-04):
se aplica directo, sin ventana de mantenimiento especial.
"""
from alembic import op
import sqlalchemy as sa

revision = '025_timestamptz_conversion'
down_revision = '024_add_audit_columns'
branch_labels = None
depends_on = None

_TABLES_CREATED_UPDATED = [
    'tenants',
    'tenant_themes',
    'tenant_applications',
    'password_policies',
]


def upgrade():
    for table in _TABLES_CREATED_UPDATED:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC'")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC'")

    op.execute("ALTER TABLE password_policies ALTER COLUMN last_synced_at TYPE timestamptz USING last_synced_at AT TIME ZONE 'UTC'")


def downgrade():
    for table in _TABLES_CREATED_UPDATED:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN created_at TYPE timestamp USING created_at AT TIME ZONE 'UTC'")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN updated_at TYPE timestamp USING updated_at AT TIME ZONE 'UTC'")

    op.execute("ALTER TABLE password_policies ALTER COLUMN last_synced_at TYPE timestamp USING last_synced_at AT TIME ZONE 'UTC'")
