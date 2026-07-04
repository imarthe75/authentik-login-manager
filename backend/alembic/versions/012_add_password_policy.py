"""Add global password_policies table (single row), seeded from the live
Authentik PasswordPolicy 'default-password-change-password-policy' values
(read 2026-07-03) so the first GET reflects reality instead of arbitrary
defaults that would silently diverge until the first save.

Revision ID: 012_add_password_policy
Revises: 011_add_tenants
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = '012_add_password_policy'
down_revision = '011_add_tenants'
branch_labels = None
depends_on = None

# authentik.policies.password.models.PasswordPolicy default symbol set —
# copiado tal cual del objeto vivo para que el primer GET coincida con lo
# que Authentik ya está aplicando.
DEFAULT_SYMBOL_CHARSET = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '

SINGLETON_ID = '00000000-0000-0000-0000-000000000001'


def upgrade():
    op.create_table(
        'password_policies',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('length_min', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('amount_uppercase', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('amount_lowercase', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('amount_digits', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('amount_symbols', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('symbol_charset', sa.Text(), nullable=False, server_default=DEFAULT_SYMBOL_CHARSET),
        sa.Column('check_zxcvbn', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('zxcvbn_score_threshold', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('check_have_i_been_pwned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.String(500), nullable=False,
                   server_default='La contraseña debe tener mínimo 10 caracteres, 1 mayúscula y 1 dígito.'),
        sa.Column('help_text', sa.Text(), nullable=False,
                   server_default="Mínimo 10 caracteres, incluye al menos 1 mayúscula y 1 número. Evita palabras comunes, nombres o patrones predecibles (fechas, secuencias como '1234')."),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Fila única (singleton) — coincide con la política global real de
    # Authentik (default-password-change-password-policy, leída en vivo).
    op.execute(
        f"""
        INSERT INTO password_policies (
            id, length_min, amount_uppercase, amount_lowercase, amount_digits,
            amount_symbols, symbol_charset, check_zxcvbn, zxcvbn_score_threshold,
            check_have_i_been_pwned, error_message, help_text, created_at, updated_at
        )
        VALUES (
            '{SINGLETON_ID}', 10, 1, 0, 1,
            0, '{DEFAULT_SYMBOL_CHARSET.replace("'", "''")}', true, 3,
            false,
            'La contraseña debe tener mínimo 10 caracteres, 1 mayúscula y 1 dígito.',
            'Mínimo 10 caracteres, incluye al menos 1 mayúscula y 1 número. Evita palabras comunes, nombres o patrones predecibles (fechas, secuencias como ''1234'').',
            now(), now()
        )
        """
    )


def downgrade():
    op.drop_table('password_policies')
