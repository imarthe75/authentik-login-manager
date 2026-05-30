"""initial schema and default flow seeding

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-05-29T12:00:00Z

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tenant_themes table
    op.create_table(
        'tenant_themes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('authentik_flow_slug', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=150), nullable=False),
        sa.Column('system_name', sa.String(length=150), nullable=False),
        sa.Column('system_subtitle', sa.String(length=255), nullable=False),
        sa.Column('layout_position', sa.String(length=10), nullable=False),
        sa.Column('name_align', sa.String(length=10), nullable=False),
        sa.Column('subtitle_align', sa.String(length=10), nullable=False),
        sa.Column('privacy_align', sa.String(length=10), nullable=False),
        sa.Column('primary_color', sa.String(length=7), nullable=False),
        sa.Column('hover_color', sa.String(length=7), nullable=False),
        sa.Column('bg_type', sa.String(length=10), nullable=False),
        sa.Column('bg_flat_color', sa.String(length=7), nullable=True),
        sa.Column('bg_gradient_from', sa.String(length=7), nullable=False),
        sa.Column('bg_gradient_to', sa.String(length=7), nullable=False),
        sa.Column('bg_image_base64', sa.Text(), nullable=True),
        sa.Column('bg_opacity', sa.Float(), nullable=False),
        sa.Column('form_opacity', sa.Float(), nullable=False),
        sa.Column('form_height_pct', sa.Integer(), nullable=True),
        sa.Column('logos_opacity', sa.Float(), nullable=False),
        sa.Column('logos_height_pct', sa.Integer(), nullable=True),
        sa.Column('logo_top_base64', sa.Text(), nullable=True),
        sa.Column('logo_bottom_base64', sa.Text(), nullable=True),
        sa.Column('privacy_pdf_url', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. Create index on authentik_flow_slug
    op.create_index(op.f('ix_tenant_themes_authentik_flow_slug'), 'tenant_themes', ['authentik_flow_slug'], unique=True)

    # 3. Seed initial default portal theme configuration
    op.execute(
        """
        INSERT INTO tenant_themes (
            id, authentik_flow_slug, display_name, system_name, system_subtitle,
            layout_position, name_align, subtitle_align, privacy_align,
            primary_color, hover_color, bg_type, bg_flat_color,
            bg_gradient_from, bg_gradient_to, bg_opacity, form_opacity,
            form_height_pct, logos_opacity, logos_height_pct,
            logo_top_base64, logo_bottom_base64, bg_image_base64,
            privacy_pdf_url, is_active, created_at, updated_at
        ) VALUES (
            'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
            'default-authentication-flow',
            'CASMARTS Core Portal',
            'CASMARTS<br>Core',
            'Gobierno del estado de México',
            'left',
            'center',
            'center',
            'center',
            '#8B3A2A',
            '#a04535',
            'gradient',
            NULL,
            '#c8c4bc',
            '#a09890',
            1.0,
            0.55,
            NULL,
            0.55,
            NULL,
            NULL,
            NULL,
            NULL,
            '/static/aviso_privacidad.pdf',
            TRUE,
            NOW(),
            NOW()
        );
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_tenant_themes_authentik_flow_slug'), table_name='tenant_themes')
    op.drop_table('tenant_themes')
