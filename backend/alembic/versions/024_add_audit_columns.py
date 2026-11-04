"""Add CASMART canonical audit columns + audit_biu trigger to the 5 shared theming tables

Revision ID: 024_add_audit_columns
Revises: 023_add_theme_fonts
Create Date: 2026-11-03

Instala el subconjunto del Estandar de auditoria CASMART (v2026.10.14,
skill postgres-audit) que se puede verificar e instalar de forma segura con
el codigo verbatim documentado en
`skills/postgres-audit/references/ESTANDAR_AUDITORIA_CASMART_v1.0.md`
seccion 7.1/7.2/7.3: columnas canonicas + trigger audit_biu
(auditoria.auditoria_biu, asignar_biu, bloqueo_optimista, reporte_cobertura).

NO instala la bitacora `auditoria.log_auditoria` (hash-chain particionado),
los event triggers (`et_grant_on_create`/`et_auditoria_ddl`/`et_auditoria_drop`)
ni el esquema `auditoria_control` (ancla + verificacion diaria via pg_cron) —
esas piezas requieren el instalador oficial
`auditoria_estandar_completo.sql` del repositorio de base de datos CASMART
(no presente en este checkout) corrido por un DBA con superusuario; faltan
piezas no documentadas explicitamente aqui (particion DEFAULT, secuencia,
orden de creacion de roles migrator/auditor/role_dev_dml) y reconstruirlas a
mano arriesga una falla silenciosa en un control de deteccion de alteracion.
Ver rules/postgres/rules.md y el reporte de auditoria 2026-11-03.
"""
from alembic import op
import sqlalchemy as sa

revision = '024_add_audit_columns'
down_revision = '023_add_theme_fonts'
branch_labels = None
depends_on = None

_TABLES = [
    'tenants',
    'tenant_themes',
    'tenant_applications',
    'tenant_email_bodies',
    'password_policies',
]

_AUDITORIA_BIU_SQL = r"""
CREATE SCHEMA IF NOT EXISTS auditoria;

CREATE OR REPLACE FUNCTION auditoria.auditoria_biu() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_ahora    timestamptz := clock_timestamp();
    v_usuario  text        := coalesce(nullif(current_setting('app.current_user', true), ''), session_user);
    v_bloqueo  boolean     := TG_NARGS > 0 AND 'bloqueo_optimista' = ANY (TG_ARGV);
    v_fila     jsonb;
    v_ant      jsonb;
    v_cambios  jsonb := '{}'::jsonb;
    v_original record;
BEGIN
    v_original := NEW;
    BEGIN
        IF TG_OP = 'INSERT' THEN
            NEW.id                   := coalesce(NEW.id, uuidv7());
            NEW.ref                  := coalesce(NEW.ref, uuidv7());
            NEW.row_version          := 1;
            NEW.fecha_creacion       := coalesce(NEW.fecha_creacion, v_ahora);
            NEW.fecha_modificacion   := NEW.fecha_creacion;
            NEW.usuario_creacion     := coalesce(NEW.usuario_creacion, v_usuario);
            NEW.usuario_modificacion := coalesce(NEW.usuario_modificacion, NEW.usuario_creacion);
            NEW.activo               := coalesce(NEW.activo, true);
            NEW.borrado              := coalesce(NEW.borrado, false);
        ELSE
            IF v_bloqueo
               AND NEW.row_version IS DISTINCT FROM OLD.row_version
               AND NEW.row_version IS DISTINCT FROM coalesce(OLD.row_version, 0) + 1 THEN
                RAISE EXCEPTION '%.%: el registro fue modificado por otra transaccion (row_version enviado %, vigente %)',
                    TG_TABLE_SCHEMA, TG_TABLE_NAME, NEW.row_version, OLD.row_version
                    USING ERRCODE = 'serialization_failure';
            END IF;
            NEW.id                 := OLD.id;
            NEW.ref                := coalesce(OLD.ref, NEW.ref, uuidv7());
            NEW.fecha_creacion     := OLD.fecha_creacion;
            NEW.usuario_creacion   := OLD.usuario_creacion;
            NEW.row_version        := coalesce(OLD.row_version, 0) + 1;
            NEW.fecha_modificacion := v_ahora;
            IF NEW.usuario_modificacion IS NULL
               OR NEW.usuario_modificacion IS NOT DISTINCT FROM OLD.usuario_modificacion THEN
                NEW.usuario_modificacion := v_usuario;
            END IF;
        END IF;
        RETURN NEW;
    EXCEPTION WHEN undefined_column THEN
        NEW := v_original;
    END;

    v_fila := to_jsonb(NEW);
    IF TG_OP = 'INSERT' THEN
        IF v_fila ? 'id'  AND v_fila->>'id'  IS NULL THEN
            v_cambios := v_cambios || jsonb_build_object('id', uuidv7());
        END IF;
        IF v_fila ? 'ref' AND v_fila->>'ref' IS NULL THEN
            v_cambios := v_cambios || jsonb_build_object('ref', uuidv7());
        END IF;
        IF v_fila ? 'row_version'          THEN v_cambios := v_cambios || jsonb_build_object('row_version', 1); END IF;
        IF v_fila ? 'fecha_creacion'       THEN v_cambios := v_cambios || jsonb_build_object('fecha_creacion', coalesce((v_fila->>'fecha_creacion')::timestamptz, v_ahora)); END IF;
        IF v_fila ? 'fecha_modificacion'   THEN v_cambios := v_cambios || jsonb_build_object('fecha_modificacion', coalesce((v_fila->>'fecha_creacion')::timestamptz, v_ahora)); END IF;
        IF v_fila ? 'usuario_creacion'     THEN v_cambios := v_cambios || jsonb_build_object('usuario_creacion', coalesce(v_fila->>'usuario_creacion', v_usuario)); END IF;
        IF v_fila ? 'usuario_modificacion' THEN v_cambios := v_cambios || jsonb_build_object('usuario_modificacion', coalesce(v_fila->>'usuario_modificacion', v_fila->>'usuario_creacion', v_usuario)); END IF;
        IF v_fila ? 'activo'  AND v_fila->>'activo'  IS NULL THEN v_cambios := v_cambios || jsonb_build_object('activo', true);  END IF;
        IF v_fila ? 'borrado' AND v_fila->>'borrado' IS NULL THEN v_cambios := v_cambios || jsonb_build_object('borrado', false); END IF;
    ELSE
        v_ant := to_jsonb(OLD);
        IF v_bloqueo AND v_fila ? 'row_version'
           AND v_fila->'row_version' IS DISTINCT FROM v_ant->'row_version'
           AND (v_fila->>'row_version')::bigint IS DISTINCT FROM coalesce((v_ant->>'row_version')::bigint, 0) + 1 THEN
            RAISE EXCEPTION '%.%: el registro fue modificado por otra transaccion (row_version enviado %, vigente %)',
                TG_TABLE_SCHEMA, TG_TABLE_NAME, v_fila->>'row_version', v_ant->>'row_version'
                USING ERRCODE = 'serialization_failure';
        END IF;
        IF v_fila ? 'id' THEN v_cambios := v_cambios || jsonb_build_object('id', v_ant->'id'); END IF;
        IF v_fila ? 'ref' THEN
            v_cambios := v_cambios || jsonb_build_object('ref', coalesce(v_ant->'ref', v_fila->'ref', to_jsonb(uuidv7())));
        END IF;
        IF v_fila ? 'fecha_creacion'     THEN v_cambios := v_cambios || jsonb_build_object('fecha_creacion', v_ant->'fecha_creacion'); END IF;
        IF v_fila ? 'usuario_creacion'   THEN v_cambios := v_cambios || jsonb_build_object('usuario_creacion', v_ant->'usuario_creacion'); END IF;
        IF v_fila ? 'row_version'        THEN v_cambios := v_cambios || jsonb_build_object('row_version', coalesce((v_ant->>'row_version')::int, 0) + 1); END IF;
        IF v_fila ? 'fecha_modificacion' THEN v_cambios := v_cambios || jsonb_build_object('fecha_modificacion', v_ahora); END IF;
        IF v_fila ? 'usuario_modificacion' THEN
            v_cambios := v_cambios || jsonb_build_object('usuario_modificacion',
                CASE WHEN v_fila->>'usuario_modificacion' IS NOT NULL
                          AND v_fila->'usuario_modificacion' IS DISTINCT FROM v_ant->'usuario_modificacion'
                     THEN v_fila->>'usuario_modificacion' ELSE v_usuario END);
        END IF;
    END IF;

    IF v_cambios <> '{}'::jsonb THEN
        NEW := jsonb_populate_record(NEW, v_cambios);
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION auditoria.asignar_biu(p_tabla text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'audit_biu'
          AND tgrelid = p_tabla::regclass
    ) THEN
        EXECUTE format(
            'CREATE TRIGGER audit_biu
             BEFORE INSERT OR UPDATE ON %s
             FOR EACH ROW EXECUTE FUNCTION auditoria.auditoria_biu()',
            p_tabla
        );
        RAISE NOTICE 'audit_biu creado en %', p_tabla;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION auditoria.bloqueo_optimista(p_tabla text, p_activar boolean DEFAULT true) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_estado "char";
BEGIN
    SELECT tgenabled INTO v_estado FROM pg_trigger WHERE tgrelid = p_tabla::regclass AND tgname = 'audit_biu';
    EXECUTE format('CREATE OR REPLACE TRIGGER audit_biu BEFORE INSERT OR UPDATE ON %s
                    FOR EACH ROW EXECUTE FUNCTION auditoria.auditoria_biu(%s)',
                   p_tabla, CASE WHEN p_activar THEN quote_literal('bloqueo_optimista') ELSE '' END);
    IF v_estado = 'D' THEN
        EXECUTE format('ALTER TABLE %s DISABLE TRIGGER audit_biu', p_tabla);
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION auditoria.reporte_cobertura() RETURNS TABLE(esquema text, tabla text, tiene_ref boolean, tiene_rv boolean, tiene_biu boolean, tiene_aiud boolean, elegible boolean, estado text)
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.schemaname::TEXT AS esquema,
        t.tablename::TEXT AS tabla,
        bool_or(c.column_name = 'ref'),
        bool_or(c.column_name = 'row_version'),
        EXISTS(SELECT 1 FROM pg_trigger tr WHERE tr.tgname='audit_biu'  AND tr.tgrelid=format('%I.%I', t.schemaname, t.tablename)::regclass),
        EXISTS(SELECT 1 FROM pg_trigger tr WHERE tr.tgname='audit_aiud' AND tr.tgrelid=format('%I.%I', t.schemaname, t.tablename)::regclass),
        bool_or(c.column_name='ref') AND bool_or(c.column_name='row_version') AND bool_or(c.column_name='fecha_creacion'),
        CASE
          WHEN NOT bool_or(c.column_name='ref') THEN 'SIN_COLUMNAS_AUDITORIA'
          WHEN NOT EXISTS(SELECT 1 FROM pg_trigger tr WHERE tr.tgname='audit_biu' AND tr.tgrelid=format('%I.%I', t.schemaname, t.tablename)::regclass)
               THEN 'PENDIENTE_BIU'
          WHEN NOT EXISTS(SELECT 1 FROM pg_trigger tr WHERE tr.tgname='audit_aiud' AND tr.tgrelid=format('%I.%I', t.schemaname, t.tablename)::regclass)
               THEN 'PENDIENTE_AIUD'
          ELSE 'COMPLETO'
        END
    FROM pg_tables t
    LEFT JOIN information_schema.columns c
        ON c.table_schema = t.schemaname AND c.table_name = t.tablename
    WHERE t.schemaname NOT IN ('information_schema', 'pg_catalog', 'auditoria', 'topology', 'tiger')
    GROUP BY t.schemaname, t.tablename
    ORDER BY t.schemaname, t.tablename;
END;
$$;
"""


def upgrade():
    op.execute(_AUDITORIA_BIU_SQL)

    for table in _TABLES:
        op.add_column(table, sa.Column('ref', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(table, sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False))
        op.add_column(table, sa.Column('borrado', sa.Boolean(), server_default=sa.false(), nullable=False))
        op.add_column(table, sa.Column('row_version', sa.Integer(), server_default='1', nullable=False))
        op.add_column(table, sa.Column('fecha_creacion', sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column('fecha_modificacion', sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column('usuario_creacion', sa.Text(), nullable=True))
        op.add_column(table, sa.Column('usuario_modificacion', sa.Text(), nullable=True))

        # Backfill de filas existentes (DEFAULT solo aplica a filas nuevas).
        # fecha_creacion/fecha_modificacion se heredan de created_at/updated_at
        # cuando existen, en vez de resetear todo a "ahora".
        has_created_at = table != 'tenant_email_bodies'
        if has_created_at:
            op.execute(f"""
                UPDATE {table} SET
                    ref = coalesce(ref, uuidv7()),
                    fecha_creacion = coalesce(fecha_creacion, created_at AT TIME ZONE 'UTC'),
                    fecha_modificacion = coalesce(fecha_modificacion, updated_at AT TIME ZONE 'UTC'),
                    usuario_creacion = coalesce(usuario_creacion, 'migracion_024'),
                    usuario_modificacion = coalesce(usuario_modificacion, 'migracion_024')
                WHERE ref IS NULL
            """)
        else:
            op.execute(f"""
                UPDATE {table} SET
                    ref = coalesce(ref, uuidv7()),
                    fecha_creacion = coalesce(fecha_creacion, clock_timestamp()),
                    fecha_modificacion = coalesce(fecha_modificacion, clock_timestamp()),
                    usuario_creacion = coalesce(usuario_creacion, 'migracion_024'),
                    usuario_modificacion = coalesce(usuario_modificacion, 'migracion_024')
                WHERE ref IS NULL
            """)

        op.alter_column(table, 'fecha_creacion', nullable=False)
        op.alter_column(table, 'fecha_modificacion', nullable=False)
        op.create_unique_constraint(f'uq_{table}_ref', table, ['ref'])
        op.execute(f"SELECT auditoria.asignar_biu('public.{table}')")


def downgrade():
    for table in _TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS audit_biu ON {table}")
        op.drop_constraint(f'uq_{table}_ref', table, type_='unique')
        for col in ('ref', 'activo', 'borrado', 'row_version', 'fecha_creacion', 'fecha_modificacion', 'usuario_creacion', 'usuario_modificacion'):
            op.drop_column(table, col)
    op.execute("DROP FUNCTION IF EXISTS auditoria.reporte_cobertura()")
    op.execute("DROP FUNCTION IF EXISTS auditoria.bloqueo_optimista(text, boolean)")
    op.execute("DROP FUNCTION IF EXISTS auditoria.asignar_biu(text)")
    op.execute("DROP FUNCTION IF EXISTS auditoria.auditoria_biu()")
    op.execute("DROP SCHEMA IF EXISTS auditoria")
