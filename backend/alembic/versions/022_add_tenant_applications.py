"""Add tenant_applications table (app<->tenant link, source of truth)

Revision ID: 022_add_tenant_applications
Revises: 021_add_field_label_color
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = '022_add_tenant_applications'
down_revision = '021_add_field_label_color'
branch_labels = None
depends_on = None


def upgrade():
    # NOTA: esta migración solo crea el esquema. La conexión de Alembic
    # apunta a la base authentik_login_manager (ver alembic/env.py) — no
    # puede alcanzar authentik_core_application, que vive en la base
    # `authentik` (otra base de datos, ver authentik_engine en admin.py), así
    # que no hay forma de calcular aquí a qué apps reales pertenece cada
    # tenant. El backfill de compatibilidad para los tenants que ya
    # existían antes de este cambio vive en
    # scripts/backfill_tenant_applications.py (correr una sola vez después
    # de este upgrade, ver docstring del script) — reproduce el filtro
    # hardcodeado que list_authentik_applications tenía antes de esta
    # migración, para no romper de golpe lo que los tenants existentes ya
    # veían en el panel. Tenants nuevos no necesitan backfill: se enlazan
    # solos vía _auto_link_unassigned_applications (admin.py) o manualmente
    # desde la pestaña Aplicaciones.
    op.create_table(
        'tenant_applications',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('application_slug', sa.String(100), nullable=False),
        sa.Column('application_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('link_source', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'application_slug', name='uq_tenant_applications_tenant_app'),
        sa.CheckConstraint(
            "link_source IN ('group_convention','manual')",
            name='ck_tenant_applications_link_source'
        ),
    )
    op.create_foreign_key(
        'fk_tenant_applications_tenant_id',
        'tenant_applications',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_tenant_applications_tenant_id', 'tenant_applications', ['tenant_id'])
    op.create_index('ix_tenant_applications_application_slug', 'tenant_applications', ['application_slug'])


def downgrade():
    op.drop_index('ix_tenant_applications_application_slug', table_name='tenant_applications')
    op.drop_index('ix_tenant_applications_tenant_id', table_name='tenant_applications')
    op.drop_constraint('fk_tenant_applications_tenant_id', 'tenant_applications', type_='foreignkey')
    op.drop_table('tenant_applications')
