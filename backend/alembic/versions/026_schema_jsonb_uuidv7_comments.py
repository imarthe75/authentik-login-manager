"""Move shared tables to schema app, JSON->JSONB, uuidv7() PK default, COMMENT ON

Revision ID: 026_schema_jsonb_uuidv7_comments
Revises: 025_timestamptz_conversion
Create Date: 2026-11-04

Resto de los hallazgos documentados-pero-no-corregidos en
docs/SECURITY_AUDIT_2026-11-04.md, autorizados por el usuario 2026-11-04
(ambiente test/QA, downtime aceptado):

- database-style.md #2: separacion por esquemas — tenants, tenant_themes,
  tenant_applications, tenant_email_bodies, password_policies se mueven de
  `public` a `app` (ALTER TABLE ... SET SCHEMA, preserva FKs/indices/
  triggers/comments). theme_app_user y admin reciben `search_path = app,
  public` a nivel de rol, asi que el codigo de la aplicacion (SQLAlchemy, sin
  schema= explicito en los modelos) sigue funcionando sin cambios — PERO
  ambos roles necesitan ademas `GRANT USAGE ON SCHEMA app` explicito (a
  diferencia de `public`, que lo trae por omision para todos — esto rompio
  el primer intento de esta migracion en caliente, se corrigio antes de
  continuar).
- postgres/rules.md #2: `id` pasa de `default=uuid.uuid4` (Python, UUIDv4)
  a `server_default=uuidv7()` (DB, UUIDv7 time-ordered) en las 5 tablas —
  SQLAlchemy necesita el server_default explicito (no solo el trigger
  audit_biu) para saber que debe pedir el valor generado de vuelta via
  RETURNING; sin esto el ORM intenta registrar el objeto con id NULL y
  lanza FlushError antes de que el trigger llegue a correr (comprobado en
  vivo). Los modelos SQLAlchemy de ambos backends se actualizaron a la vez
  — ver commits de authentik-login-manager/authentik-login-designer.
- postgres/rules.md #2: `tenants.config`, `tenant_themes.custom_messages`,
  `tenant_themes.expansion_config` de `json` a `jsonb`.
- postgres/rules.md #6 / database-style.md #6: `COMMENT ON` en las 5 tablas
  y sus columnas canonicas de auditoria (id/ref/activo/borrado/row_version/
  fecha_creacion/fecha_modificacion/usuario_creacion/usuario_modificacion).

Verificado en vivo end-to-end despues de cada paso: lecturas, un UPDATE real
(row_version incrementa, aparece en auditoria.log_auditoria), y
auditoria.fn_verificar_cadena() sigue en 0 filas (cadena intacta).
"""
from alembic import op
import sqlalchemy as sa

revision = '026_schema_jsonb_uuidv7_comments'
down_revision = '025_timestamptz_conversion'
branch_labels = None
depends_on = None

_TABLES = [
    'tenants',
    'tenant_themes',
    'tenant_applications',
    'tenant_email_bodies',
    'password_policies',
]

_TABLE_COMMENTS = {
    'tenants': 'Tenants (marcas) del ecosistema CaSmarts de login — uno por dominio de Authentik (auth.*.ca-smarts.com), compartida entre authentik-login-manager y authentik-login-designer.',
    'tenant_themes': 'Tema visual de login por flujo/app de Authentik (authentik_flow_slug + authentik_app_slug opcional) — colores, fuentes, logos, textos legales.',
    'tenant_applications': 'Aplicaciones de Authentik enlazadas a un tenant (manual o por convencion de grupo) — determina de que tenant es el branding de una app.',
    'tenant_email_bodies': 'Cuerpos de correo personalizados por tenant/flow/tipo de evento (alta, recuperacion de contrasena, etc.) — plantilla HTML enviada por Authentik.',
    'password_policies': 'Politica de contrasenas (singleton, una fila) — se sincroniza con el PasswordPolicy real de Authentik via la API.',
}

_AUDIT_COLUMN_COMMENTS = {
    'id': 'PK, uuidv7() (time-ordered) — Estandar de auditoria CASMART.',
    'ref': 'UUIDv7 estable para sincronizacion externa, distinto de id. Estandar de auditoria CASMART.',
    'activo': 'Bandera de activo/inactivo (soft toggle). Estandar de auditoria CASMART.',
    'borrado': 'Borrado logico — los listados deben filtrar por borrado=false. Estandar de auditoria CASMART.',
    'row_version': 'Bloqueo optimista, incrementado por el trigger audit_biu en cada UPDATE. Estandar de auditoria CASMART.',
    'fecha_creacion': 'timestamptz de creacion, asignado por el trigger audit_biu. Estandar de auditoria CASMART.',
    'fecha_modificacion': 'timestamptz de la ultima modificacion, asignado por el trigger audit_biu. Estandar de auditoria CASMART.',
    'usuario_creacion': 'Usuario/caller que creo la fila (GUC app.current_user o session_user). Estandar de auditoria CASMART.',
    'usuario_modificacion': 'Usuario/caller de la ultima modificacion (GUC app.current_user o session_user). Estandar de auditoria CASMART.',
}


def upgrade():
    # 1. Esquema app + mover las 5 tablas
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("COMMENT ON SCHEMA app IS 'Dominio transaccional de la aplicacion (database-style.md #2) — tablas de negocio de login-manager/login-designer.'")
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} SET SCHEMA app")

    op.execute("GRANT USAGE ON SCHEMA app TO theme_app_user")
    op.execute("ALTER ROLE theme_app_user SET search_path TO app, public")
    op.execute("ALTER ROLE admin SET search_path TO app, public")

    # 2. uuidv7() como server_default de id (reemplaza la generacion client-side)
    for table in _TABLES:
        op.execute(f"ALTER TABLE app.{table} ALTER COLUMN id SET DEFAULT uuidv7()")

    # 3. json -> jsonb
    op.execute("ALTER TABLE app.tenants ALTER COLUMN config TYPE jsonb USING config::jsonb")
    op.execute("ALTER TABLE app.tenant_themes ALTER COLUMN custom_messages TYPE jsonb USING custom_messages::jsonb")
    op.execute("ALTER TABLE app.tenant_themes ALTER COLUMN expansion_config TYPE jsonb USING expansion_config::jsonb")

    # 4. COMMENT ON
    for table, comment in _TABLE_COMMENTS.items():
        op.execute(sa.text(f"COMMENT ON TABLE app.{table} IS :c").bindparams(c=comment))
    for table in _TABLES:
        for column, comment in _AUDIT_COLUMN_COMMENTS.items():
            op.execute(sa.text(f"COMMENT ON COLUMN app.{table}.{column} IS :c").bindparams(c=comment))


def downgrade():
    for table in _TABLES:
        op.execute(f"ALTER TABLE app.{table} ALTER COLUMN id DROP DEFAULT")

    op.execute("ALTER TABLE app.tenants ALTER COLUMN config TYPE json USING config::json")
    op.execute("ALTER TABLE app.tenant_themes ALTER COLUMN custom_messages TYPE json USING custom_messages::json")
    op.execute("ALTER TABLE app.tenant_themes ALTER COLUMN expansion_config TYPE json USING expansion_config::json")

    op.execute("ALTER ROLE theme_app_user RESET search_path")
    op.execute("ALTER ROLE admin RESET search_path")

    for table in _TABLES:
        op.execute(f"ALTER TABLE app.{table} SET SCHEMA public")
