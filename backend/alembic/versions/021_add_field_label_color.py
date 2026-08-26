"""Add field_label_color column

Revision ID: 021_add_field_label_color
Revises: 020_add_logo_text_styling
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa

revision = '021_add_field_label_color'
down_revision = '020_add_logo_text_styling'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenant_themes', sa.Column('field_label_color', sa.String(length=7), server_default='#374151', nullable=False))


def downgrade():
    op.drop_column('tenant_themes', 'field_label_color')
