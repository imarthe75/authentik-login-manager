"""add access+notifications columns and tenant_email_bodies table

Revision ID: 006_add_access_and_notifications
Revises: 005_add_logo_text_fields
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '006_add_access_and_notifications'
down_revision: str = '005_add_logo_text_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenant_themes', sa.Column(
        'allow_self_registration', sa.Boolean(), nullable=False,
        server_default=sa.text('false')
    ))
    op.add_column('tenant_themes', sa.Column(
        'require_email_verification', sa.Boolean(), nullable=False,
        server_default=sa.text('true')
    ))
    op.add_column('tenant_themes', sa.Column(
        'show_social_google', sa.Boolean(), nullable=False,
        server_default=sa.text('false')
    ))
    op.add_column('tenant_themes', sa.Column(
        'show_social_microsoft', sa.Boolean(), nullable=False,
        server_default=sa.text('false')
    ))
    op.add_column('tenant_themes', sa.Column(
        'show_social_gov_id', sa.Boolean(), nullable=False,
        server_default=sa.text('false')
    ))
    op.add_column('tenant_themes', sa.Column(
        'email_footer_text', sa.String(255), nullable=True
    ))
    op.add_column('tenant_themes', sa.Column(
        'email_template_type', sa.String(20), nullable=False,
        server_default=sa.text("'integrated'")
    ))
    op.create_check_constraint(
        'ck_tenant_themes_email_template_type',
        'tenant_themes',
        "email_template_type IN ('integrated', 'custom_per_event')"
    )

    op.create_table(
        'tenant_email_bodies',
        sa.Column(
            'id', postgresql.UUID(as_uuid=True), nullable=False,
            server_default=sa.text('gen_random_uuid()')
        ),
        sa.Column('flow_slug', sa.String(100), nullable=False),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('subject', sa.String(200), nullable=False, server_default=''),
        sa.Column('body_html', sa.Text(), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flow_slug', 'event_type', name='uq_email_bodies_flow_event'),
        sa.CheckConstraint(
            "event_type IN ('password_reset','new_account','account_lockout',"
            "'email_verification','security_change')",
            name='ck_email_bodies_event_type'
        )
    )
    op.create_index('ix_tenant_email_bodies_flow_slug', 'tenant_email_bodies', ['flow_slug'])


def downgrade() -> None:
    op.drop_index('ix_tenant_email_bodies_flow_slug', 'tenant_email_bodies')
    op.drop_table('tenant_email_bodies')
    op.drop_constraint('ck_tenant_themes_email_template_type', 'tenant_themes', type_='check')
    op.drop_column('tenant_themes', 'email_template_type')
    op.drop_column('tenant_themes', 'email_footer_text')
    op.drop_column('tenant_themes', 'show_social_gov_id')
    op.drop_column('tenant_themes', 'show_social_microsoft')
    op.drop_column('tenant_themes', 'show_social_google')
    op.drop_column('tenant_themes', 'require_email_verification')
    op.drop_column('tenant_themes', 'allow_self_registration')
