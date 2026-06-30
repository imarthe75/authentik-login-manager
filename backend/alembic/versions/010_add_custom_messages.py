"""Add custom messages JSON column

Revision ID: 010_add_custom_messages
Revises: 009_add_show_app_message
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

revision = '010_add_custom_messages'
down_revision = '009_add_show_app_message'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('tenant_themes', sa.Column('custom_messages', sa.JSON(), server_default='{}', nullable=False))

def downgrade():
    op.drop_column('tenant_themes', 'custom_messages')
