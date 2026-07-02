"""Add Multi-Tenant support with Tenants table and relations

Revision ID: 011_add_tenants
Revises: 010_add_custom_messages
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = '011_add_tenants'
down_revision = '010_add_custom_messages'
branch_labels = None
depends_on = None


def upgrade():
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('name', sa.String(150), nullable=False, unique=True),
        sa.Column('domain_pattern', sa.String(255), nullable=False, unique=True),
        sa.Column('logo_email_base64', sa.Text(), nullable=True),
        sa.Column('primary_color', sa.String(7), nullable=False, server_default='#4272A5'),
        sa.Column('secondary_color', sa.String(7), nullable=False, server_default='#2d5580'),
        sa.Column('config', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_tenants_name'),
        sa.UniqueConstraint('domain_pattern', name='uq_tenants_domain_pattern'),
    )

    # Create indexes on tenants
    op.create_index('ix_tenants_name', 'tenants', ['name'])
    op.create_index('ix_tenants_domain_pattern', 'tenants', ['domain_pattern'])
    op.create_index('ix_tenants_is_active', 'tenants', ['is_active'])

    # Insert default CASMARTS tenant
    op.execute(
        """
        INSERT INTO tenants (id, name, domain_pattern, primary_color, secondary_color, is_active, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000001', 'CASMARTS', 'casmarts.local', '#4272A5', '#2d5580', true, now(), now())
        """
    )

    # Add tenant_id column to tenant_themes (initially nullable)
    op.add_column('tenant_themes', sa.Column('tenant_id', UUID(as_uuid=True), nullable=True))

    # Create foreign key for tenant_themes.tenant_id
    op.create_foreign_key(
        'fk_tenant_themes_tenant_id',
        'tenant_themes',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Create index on tenant_themes.tenant_id
    op.create_index('ix_tenant_themes_tenant_id', 'tenant_themes', ['tenant_id'])

    # Create composite index on tenant_themes
    op.create_index(
        'ix_tenant_themes_tenant_flow',
        'tenant_themes',
        ['tenant_id', 'authentik_flow_slug']
    )

    # Update existing tenant_themes to reference default tenant
    op.execute(
        """
        UPDATE tenant_themes
        SET tenant_id = '00000000-0000-0000-0000-000000000001'
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id NOT NULL
    op.alter_column('tenant_themes', 'tenant_id', nullable=False)

    # Add tenant_id column to tenant_email_bodies (initially nullable)
    op.add_column('tenant_email_bodies', sa.Column('tenant_id', UUID(as_uuid=True), nullable=True))

    # Create foreign key for tenant_email_bodies.tenant_id
    op.create_foreign_key(
        'fk_tenant_email_bodies_tenant_id',
        'tenant_email_bodies',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Create index on tenant_email_bodies.tenant_id
    op.create_index('ix_tenant_email_bodies_tenant_id', 'tenant_email_bodies', ['tenant_id'])

    # Create composite index on tenant_email_bodies
    op.create_index(
        'ix_tenant_email_bodies_tenant_flow_event',
        'tenant_email_bodies',
        ['tenant_id', 'flow_slug', 'event_type']
    )

    # Update existing tenant_email_bodies to reference default tenant
    op.execute(
        """
        UPDATE tenant_email_bodies
        SET tenant_id = '00000000-0000-0000-0000-000000000001'
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id NOT NULL
    op.alter_column('tenant_email_bodies', 'tenant_id', nullable=False)

    # Drop old unique constraint on tenant_email_bodies and create new one with tenant_id
    op.drop_constraint('uq_email_bodies_flow_event', 'tenant_email_bodies', type_='unique')
    op.create_unique_constraint(
        'uq_email_bodies_tenant_flow_event',
        'tenant_email_bodies',
        ['tenant_id', 'flow_slug', 'event_type']
    )


def downgrade():
    # Drop composite index on tenant_email_bodies
    op.drop_index('ix_tenant_email_bodies_tenant_flow_event', table_name='tenant_email_bodies')

    # Drop index on tenant_email_bodies.tenant_id
    op.drop_index('ix_tenant_email_bodies_tenant_id', table_name='tenant_email_bodies')

    # Drop foreign key for tenant_email_bodies.tenant_id
    op.drop_constraint('fk_tenant_email_bodies_tenant_id', 'tenant_email_bodies', type_='foreignkey')

    # Restore old unique constraint
    op.drop_constraint('uq_email_bodies_tenant_flow_event', 'tenant_email_bodies', type_='unique')
    op.create_unique_constraint(
        'uq_email_bodies_flow_event',
        'tenant_email_bodies',
        ['flow_slug', 'event_type']
    )

    # Drop tenant_id column from tenant_email_bodies
    op.drop_column('tenant_email_bodies', 'tenant_id')

    # Drop composite index on tenant_themes
    op.drop_index('ix_tenant_themes_tenant_flow', table_name='tenant_themes')

    # Drop index on tenant_themes.tenant_id
    op.drop_index('ix_tenant_themes_tenant_id', table_name='tenant_themes')

    # Drop foreign key for tenant_themes.tenant_id
    op.drop_constraint('fk_tenant_themes_tenant_id', 'tenant_themes', type_='foreignkey')

    # Drop tenant_id column from tenant_themes
    op.drop_column('tenant_themes', 'tenant_id')

    # Drop indexes on tenants
    op.drop_index('ix_tenants_is_active', table_name='tenants')
    op.drop_index('ix_tenants_domain_pattern', table_name='tenants')
    op.drop_index('ix_tenants_name', table_name='tenants')

    # Drop tenants table
    op.drop_table('tenants')
