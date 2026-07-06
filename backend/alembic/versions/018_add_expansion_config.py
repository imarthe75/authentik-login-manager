"""Add expansion_config JSON column

Revision ID: 018_add_expansion_config
Revises: 017_add_more_event_types
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = '018_add_expansion_config'
down_revision = '017_add_more_event_types'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('tenant_themes', sa.Column('expansion_config', sa.JSON(), server_default='{}', nullable=True))

def downgrade():
    op.drop_column('tenant_themes', 'expansion_config')
