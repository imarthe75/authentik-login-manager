"""005_add_logo_text_fields: add logo_top_text and logo_bottom_text columns

Revision ID: 005_add_logo_text_fields
Revises: 004_multi_app_per_flow
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa

revision: str = '005_add_logo_text_fields'
down_revision: str = '004_multi_app_per_flow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenant_themes', sa.Column('logo_top_text', sa.Text(), nullable=True))
    op.add_column('tenant_themes', sa.Column('logo_bottom_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tenant_themes', 'logo_bottom_text')
    op.drop_column('tenant_themes', 'logo_top_text')
