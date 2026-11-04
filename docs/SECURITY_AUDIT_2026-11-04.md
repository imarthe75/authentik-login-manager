# Auditoría de Seguridad y Cumplimiento CASMART — Ecosistema completo
**Fecha:** 2026-11-03/04/05 · **Alcance:** `authentik-login-manager`, `authentik-login-designer`, PostgreSQL compartido (`authentik_login_manager`), Vault, gateway (`core-casmarts`), y verificación cruzada en `centinela-ai`, `consulta-smart`, `idp-smart`, `lexivault-ai` · **Método:** instalación del kit de reglas CASMART + 4 auditorías paralelas contra ese catálogo + corrección en vivo, en ambiente **test/QA** (downtime autorizado por el usuario, dueño de los 4 proyectos externos verificados).

Ver también: `authentik-login-designer/docs/SECURITY_AUDIT_2026-11-04.md` (mismo documento, referenciado desde ambos repos porque casi todos los hallazgos son del ecosistema compartido, no de un solo repositorio).

---

## Resumen ejecutivo

| Área | Hallazgos | Corregidos | Pendientes (requieren decisión externa) |
|---|---|---|---|
| Código (ambos backends) | 5 | 5 | 0 |
| PostgreSQL | 11 | 11 | 0 — bitácora completa, esquema `app`, `uuidv7()`, JSONB, `COMMENT ON`, todo instalado y verificado |
| Vault (este ecosistema) | 6 | 2 (de-hardcode + verificación) | 4 (TLS, rotación, no-root, puertos — comparten valor actual 4 proyectos reales, requiere migración coordinada, no un fix puntual) |
| Vault (proyectos externos) | 2 | 2 (permisos `.env`, integración rota en `lexivault-ai`) | 0 |
| Gateway | 4 | 4 | 0 |

---

## 1. Código — login-manager / login-designer

| # | Hallazgo | Severidad | Corrección |
|---|---|---|---|
| 1 | `GET /tenant/list` (manager) sin `verify_admin_key` — enumeraba tenants y disparaba sync con Authentik sin autenticación | Alto | `dependencies=[Depends(verify_admin_key)]` agregado |
| 2 | `GET /blueprint/download` (manager Y designer) sin `verify_admin_key` | Medio/Crítico | Mismo fix en ambos |
| 3 | `GET /blueprint/download` (designer) — `brand_name`/`domain` interpolados sin escapar en YAML de blueprint (inyección) | Crítico | Portado el validador `_BLUEPRINT_NAME_RE`/`_BLUEPRINT_DOMAIN_RE` de manager |
| 4 | `DELETE /tenant/applications/{id}` (designer) sin filtrar por `tenant_id` — IDOR sobre tabla compartida con manager | Alto | Filtro `tenant_id == DEFAULT_TENANT_ID` agregado |
| 5 | Logger de errores 422 (manager) podía escribir campos sensibles (password/token/key) en el log de texto | Alto | Redacción por nombre de campo (`_SENSITIVE_FIELD_RE`) |

**Nota de honestidad:** `authentik-login-manager` no está desplegado en este host — los fixes 1, 2 y 5 se verificaron por sintaxis (`py_compile`) y por el mismo patrón ya confirmado en vivo en `authentik-login-designer` (fixes 2, 3 y 4 sí se probaron en vivo ahí). No se declara "verificado en producción" para lo que no corrió realmente.

## 2. PostgreSQL (`authentik_login_manager`, compartida entre ambos backends)

| # | Hallazgo | Severidad | Corrección |
|---|---|---|---|
| 1 | Ambos backends conectaban como `admin`, el **superusuario** que también usa Authentik | Alto | Rol `theme_app_user` creado con GRANT acotado a las 5 tablas; `.env` de ambos backends migrado; `admin` denegado explícitamente en la base `authentik` |
| 2 | `pg_hba.conf` **real** (vive en el volumen PGDATA, `/var/lib/postgresql/data/pgdata/pg_hba.conf` — el archivo `core-casmarts/db/pg_hba.conf` del repo **no está montado y no es el que usa el contenedor**) aceptaba cualquier IP (`host all all all scram-sha-256`) | Alto | Restringido a `172.18.0.0/16` (red Docker `identity-network`) |
| 3 | `docker-compose.yml` con contraseña por omisión insegura (`:-casmarts_secure_pwd_2026`) | Alto | Eliminado el default; falla si `.env` no la define |
| 4 | Puerto 5433 de Postgres publicado al host sin necesidad | Alto | Despublicado |
| 5 | Sin columnas canónicas de auditoría ni triggers en `tenants`/`tenant_themes`/`tenant_applications`/`tenant_email_bodies`/`password_policies` | Alto | **Estándar de auditoría CASMART completo instalado**: esquema `auditoria` (21 funciones), bitácora `auditoria.log_auditoria` particionada con cadena de hash SHA-256, 3 event triggers, esquema `auditoria_control` con ancla, verificación diaria (sidecar `auditoria-cron` en vez de `pg_cron`, no disponible en esta imagen). `audit_biu` + `audit_aiud` habilitados en las 5 tablas — ver §3 |
| 6 | PKs usaban `default=uuid.uuid4()` del lado de Python (UUIDv4) | Bajo | **Corregido 2026-11-04** (migración `026_schema_jsonb_uuidv7_comments`) — `server_default=uuidv7()` a nivel de columna en las 5 tablas (ambos backends); no se regeneraron los valores de filas existentes (eso sí sería invasivo e innecesario), solo la generación de valores nuevos |
| 7 | Todo en el esquema `public`, sin separación `app`/`ref`/`auditoria` | Medio | **Corregido 2026-11-04** — las 5 tablas movidas a esquema `app` (`ALTER TABLE ... SET SCHEMA`, preserva FKs/índices/triggers/comments); `theme_app_user`/`admin` con `search_path=app,public` a nivel de rol para que el código no necesite cambios de esquema explícitos. Requirió un `GRANT USAGE ON SCHEMA app` adicional (a diferencia de `public`, que lo trae por omisión) — se encontró en caliente cuando el primer intento rompió todas las queries, corregido antes de continuar |
| 8 | `created_at`/`updated_at`/`last_synced_at` eran `timestamp` sin zona | Medio | Convertidas a `timestamptz` (base ya está en `TimeZone=UTC`, conversión exacta); modelos SQLAlchemy actualizados a `DateTime(timezone=True)` en ambos repos |
| 9 | `tenant_themes.custom_messages`/`expansion_config`/`tenants.config` en `JSON` en vez de `JSONB` | Medio | **Corregido 2026-11-04** — `ALTER COLUMN ... TYPE jsonb USING ...::jsonb`, sin pérdida de datos |
| 10 | Sin `COMMENT ON` en tablas/columnas | Medio | **Corregido 2026-11-04** — `COMMENT ON` en las 5 tablas de negocio y sus 9 columnas canónicas de auditoría (más lo ya agregado en `auditoria_control.ancla`) |
| 11 | La app nunca fijaba `set_config('app.current_user', ...)` | Alto | Agregado en `database.py` de ambos backends (IP del caller, vía `get_db`) — ver evidencia §3 |
| — | Base `authentik_login_designer` huérfana (sin tablas) + `.env.example` desactualizado apuntándole | Bajo | **Corregido** — `DROP DATABASE authentik_login_designer` ejecutado 2026-11-04; `.env.example` corregido |

### Pendiente manual
```sql
-- Ejecutar directo contra el cluster (DROP DATABASE no se pudo ejecutar desde este agente):
DROP DATABASE authentik_login_designer;
```

## 3. Evidencia de verificación (bitácora de auditoría)

Probado primero en una base descartable (`zz_audit_test`), luego en `authentik_login_manager`:
- INSERT/UPDATE/DELETE reales a través de la app → `row_version` incrementa, `usuario_modificacion` refleja el caller real (`login_designer_admin:<ip>`), la fila aparece en `auditoria.log_auditoria`.
- `auditoria.fn_verificar_cadena()` → 0 filas (cadena íntegra) después de cada prueba.
- Intento directo de `UPDATE`/`DELETE`/`TRUNCATE` sobre `auditoria.log_auditoria` → rechazado con `insufficient_privilege` (bitácora inmutable, incluso para el dueño).
- Conflicto de `row_version` (bloqueo optimista) → `SQLSTATE 40001` (mapear a HTTP 409 en el backend si se usa `bloqueo_optimista()` sobre alguna tabla; no activado por defecto, igual que el estándar).
- Tabla nueva (`CREATE TABLE ... row_version ...`) → `et_grant_on_create` le asigna `audit_biu`/`audit_aiud`/`audit_truncate` automáticamente, sin intervención manual.
- `auditoria_control.fn_verificar_y_anclar()` → corre correctamente (sidecar `auditoria-cron`, diario 02:30; `pg_cron` no está disponible en `postgres:18-alpine`, así que no se usó el mecanismo original del estándar).

**Consulta de salud diaria:**
```sql
SELECT * FROM auditoria.fn_verificar_cadena();   -- 0 filas = íntegra
SELECT * FROM auditoria.reporte_cobertura();      -- estado por tabla
SELECT * FROM auditoria_control.ancla ORDER BY fecha DESC LIMIT 5;
```

**Desviación documentada del estándar:** no existe un rol `migrator` con login propio en este proyecto (las migraciones corren como `admin`). El esquema `auditoria` quedó a nombre de `admin` (superusuario) en vez de transferirse a `migrator` — los superusuarios no están sujetos a los permisos del estándar de todos modos (§10 del estándar). `theme_app_user` recibió los mismos `GRANT EXECUTE` que el estándar documenta para `app_web_user`/`role_dev_dml`.

## 4. Vault (`core-casmarts/vault`)

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| 1 | Root token, unseal key y OIDC client secret en texto plano en `docker-compose.yml`/`configure-oidc.sh` | Crítico | **Corregido** — movidos a `core-casmarts/.env`, Vault recreado y verificado desbloqueado/autenticando con los valores vía variable |
| 2 | TLS deshabilitado en el listener de Vault (`tls_disable = true`), puerto 8200 publicado al host | Crítico | **No corregido** — ahora confirmado y verificado por SSH que `centinela-ai` (10.4.3.34) y `consulta-smart`/`idp-smart`/`lexivault-ai` (10.4.3.31) alcanzan Vault por HTTP plano con el token actual; cerrar esto rompe esos 4 servicios sin una migración coordinada de los 4 a la vez — queda pendiente como proyecto aparte, no un fix de esta ronda |
| 3 | Contenedor Vault corre como `root` | Alto | No corregido — mismo motivo |
| 4 | Vault provisionado pero los backends de este ecosistema no leen secretos de ahí (flujo real vía `.env`) | Alto | No corregido para login-manager/login-designer (cambio arquitectónico mayor); **sí corregido en `lexivault-ai`** — tenía la integración con Vault completamente rota desde su creación (bug de path duplicado en `vault_client.get_secret()` + token de "modo dev" inválido contra este Vault real) y cayendo siempre al fallback de variables de entorno sin que nadie lo notara; ver `docs/SECURITY_AUDIT_2026-11-04.md` commit `b47084d` de ese repo |
| 5 | Rotación del root token / unseal key | — | No ejecutada — los 4 proyectos de la nota anterior comparten el valor actual; rotar requiere actualizarlo en los 4 a la vez |
| 6 | `vault-init-keys.txt` como archivo permanente en texto plano (permisos 600, no es repo git) | Bajo | No corregido — artefacto de bootstrap que debería moverse a custodia real y destruirse |
| — | `.env` con permisos `664` (legible por cualquier usuario del servidor) en `consulta-smart`, `idp-smart`, `lexivault-ai` | Medio | **Corregido** — `chmod 600` en los 3 |
| — | Nueva guía de incorporación para desarrolladores | — | `core-casmarts/vault/VAULT_GUIA_INTERNA.md` (NO versionada en git) — qué es Vault, sealed/unsealed, credenciales reales, cómo conectarse y usarlo paso a paso, buenas prácticas, advertencia de que es compartido |

## 5. Gateway (`core-casmarts/gateway`)

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| 1 | Sin cabeceras de seguridad (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP) | Medio | **Corregido** a nivel `http {}` en `nginx.conf` — cubre toda ruta que no declare su propio `add_header` |
| 2 | `Access-Control-Allow-Origin: '*'` en 2 bloques `/lm/` de `subdomains.conf` | Alto | **Corregido** — cambiado a `"$scheme://$host"` (origen validado por SNI del server block) |
| 3 | `subdomains.conf.bak-20260819153257` dentro de `sites-enabled/` | Bajo | **Eliminado 2026-11-04** |
| 4 | nginx no hereda `add_header` hacia un `location`/`server` que ya declare el suyo propio (`core.conf`, partes de `subdomains.conf`) | Medio | No corregido — requeriría repetir las 5 cabeceras en cada uno de esos bloques; riesgo de romper un gateway en vivo que sirve el SSO real no se justificó para esta ronda |

---

## 6. Cómo verificar que todo sigue vivo

```bash
# Auditoría: cadena intacta
docker exec casmarts-core-db-primary psql -U admin -d authentik_login_manager -c "SELECT * FROM auditoria.fn_verificar_cadena();"

# Cobertura de auditoría por tabla
docker exec casmarts-core-db-primary psql -U admin -d authentik_login_manager -c "SELECT * FROM auditoria.reporte_cobertura();"

# Rol de la app NO es admin
docker exec casmarts-core-db-primary psql -U admin -d authentik_login_manager -c "SELECT rolname FROM pg_roles WHERE rolname = 'theme_app_user';"

# pg_hba.conf real (vive en el volumen, no en el repo)
docker exec casmarts-core-db-primary psql -U admin -d authentik -c "SELECT * FROM pg_hba_file_rules;"

# Vault sigue desbloqueado
docker exec casmarts-core-vault vault status

# Cabeceras de seguridad del gateway
curl -sk -D - https://localhost/ -o /dev/null | grep -iE "strict-transport|x-content-type|x-frame"
```
