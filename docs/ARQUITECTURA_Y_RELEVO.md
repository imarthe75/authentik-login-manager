# Arquitectura del ecosistema CaSmarts y guía de relevo — login-manager / login-designer

> Este documento es idéntico en los dos repos (`authentik-login-manager/docs/` y
> `authentik-login-designer/docs/`) — se duplica a propósito para que quien solo tenga clonado uno
> de los dos no se quede sin la mitad de la imagen (ambos comparten la misma base de datos física,
> ver §2.3). Si editas uno, replica el cambio en el otro.
>
> Este documento SÍ se sube a git (no contiene credenciales). Si buscas datos de conexión reales
> (tokens, contraseñas, direcciones con credenciales embebidas), esos viven en documentos internos
> que no se versionan — pregunta al equipo de infraestructura por la guía de Vault y los `.env`
> reales de cada entorno.
>
> Última actualización: 2026-11-04.

## Índice

1. [Arquitectura del ecosistema CaSmarts](#1-arquitectura-del-ecosistema-casmarts)
2. [`authentik-login-manager` — guía de relevo](#2-authentik-login-manager--guía-de-relevo-para-quien-continúe-el-proyecto)
3. [`authentik-login-designer` — notas de relevo](#3-authentik-login-designer--notas-de-relevo)

---

## 1. Arquitectura del ecosistema CaSmarts

Esta sección explica cómo embonan entre sí todas las piezas que corren en el servidor de identidad
del ecosistema (10.4.3.208) y en los demás servidores relacionados. Es la foto completa — útil tanto
si vas a tocar este proyecto como cualquier otra parte del ecosistema.

### 1.1 Mapa de servidores

| Servidor | Qué corre ahí | Rol |
|---|---|---|
| **10.4.3.208** | `core-casmarts` (gateway, Postgres, Valkey, Authentik, Vault), `authentik-login-manager`, `authentik-login-designer` | Identidad central del ecosistema CaSmarts — SSO, gestión de temas de login, almacén de secretos compartido |
| **10.4.3.34** | `centinela-ai` | Cliente del Vault de 10.4.3.208, consumidor de Authentik como SSO |
| **10.4.3.31** | `consulta-smart`, `lexivault-ai`, `idp-smart`, "chat" | Clientes del Vault de 10.4.3.208; `lexivault-ai` además es cliente de Authentik |
| **10.4.3.10** | GitLab interno (`gitlab.casmart.internal`) | Remoto git secundario de varios proyectos (además de GitHub) |

No todos estos servidores están documentados aquí a fondo — este documento solo describe en detalle
lo que vive en 10.4.3.208, que es la base de identidad del resto.

### 1.2 Qué corre en 10.4.3.208, y cómo se conecta

```
                            Internet / red interna
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   casmarts-core-gateway         │  nginx — reverse proxy único,
                    │   (vhosts auth.*.ca-smarts.com,  │  termina TLS, enruta por dominio.
                    │    starter.ca-smarts.com, etc.)  │  Tiene su PROPIO motor de branding
                    └───────────────┬─────────────────┘  para páginas SSR (access-denied,
                                    │                      errores) vía custom_authentik.js
                      ┌─────────────┼─────────────────────┐
                      ▼             ▼                     ▼
          ┌───────────────────┐ ┌─────────────────┐  ┌──────────────────────┐
          │ authentik-server/  │ │ casmarts-login-  │  │ authentik-login-      │
          │ authentik-worker   │ │ backend+frontend │  │ designer-backend+     │
          │ (SSO: OIDC/SAML,   │ │ (Login Manager,  │  │ frontend (Designer,   │
          │ flows, políticas)  │ │  React, multi-    │  │  Angular, single-     │
          │                    │ │  tenant)          │  │  tenant)              │
          └─────────┬──────────┘ └────────┬──────────┘  └──────────┬───────────┘
                     │                    │                         │
                     │     ┌──────────────┴───────────┐             │
                     │     │   volumen compartido       │◄────────────┘
                     │     │ custom-templates/if/        │   AMBOS /deploy escriben
                     └────►│ flow.html — Authentik lo    │   el MISMO archivo —
                            │ sirve como SPA executor.    │   ver §1.3, es colisión
                            │ JS interno hace fetch en    │   real, no aislamiento
                            │ vivo a /lm/api/.../theme/…   │
                            └─────────────────────────────┘
                     │                    │                         │
                     ▼                    ▼                         ▼
          ┌────────────────────────────────────────────────────────────────┐
          │              casmarts-core-db-primary (PostgreSQL 18.6)          │
          │  • BD `authentik` — propia de Authentik                         │
          │  • BD `authentik_login_manager` — COMPARTIDA por Manager y       │
          │    Designer (ver §2.3 — es la misma base física, no una copia)  │
          └────────────────────────────────────────────────────────────────┘
                     │                    │                         │
                     ▼                    ▼                         ▼
          ┌────────────────────────────────────────────────────────────────┐
          │                 casmarts-core-cache (Valkey)                    │
          │       caché de sesiones de Authentik + caché de temas/          │
          │       resolución de tenant por dominio (login-manager)         │
          └────────────────────────────────────────────────────────────────┘

          ┌────────────────────────────────────────────────────────────────┐
          │  casmarts-core-vault + casmarts-core-vault-unsealer              │
          │  Compartido por centinela-ai, consulta-smart, lexivault-ai,     │
          │  idp-smart — NO lo usan hoy authentik-login-manager/designer    │
          │  (siguen con `.env`; ver §2.7, es una brecha documentada)       │
          └────────────────────────────────────────────────────────────────┘
```

Todo esto vive en `core-casmarts/docker-compose.yml` (servicios: `gateway`, `db-primary`, `cache`,
`authentik-server`, `authentik-worker`, `vault`, `vault-unsealer`, `auditoria-cron`) más dos
`compose.yml` independientes, uno por cada app de login (`authentik-login-manager/compose.yml`,
`authentik-login-designer/docker-compose.yml`). Las tres piezas comparten dos redes Docker
**externas** (`identity-network` y `aura-network`) — "externas" quiere decir que no las crea ningún
`compose.yml` individual, ya existen en Docker y cada proyecto solo se conecta a ellas por nombre.

> **Nota sobre el "Resident Agent Framework" de `CLAUDE.md`:** el `CLAUDE.md` raíz del ecosistema
> menciona MinIO, Celery y un framework de agente residente con memoria vectorial
> (`memory/long_term_memory.py`, pgvector). Ese framework corre en contenedores separados
> (`resident-postgres-memory`, `resident-valkey-cache`) y **no forma parte de la base de identidad**
> descrita arriba — es infraestructura aparte para agentes de IA, no algo que `login-manager` o
> `login-designer` consuman. No lo confundas con `db-primary`/`cache` de arriba, son bases distintas.

### 1.3 Dos motores de branding — comparten un archivo, y eso YA causó bugs reales

> Verificado contra el código y los archivos reales en disco — ver también
> `docs/LOGIN_MANAGER_GUIA_TECNICA.html` y el addendum 2026-11-03 de
> `docs/REPORTE_MEJORAS_UI_AUTHENTIK.md` para más detalle.

**El mecanismo real:**

1. **`flow.html`** — un único archivo físico, compartido:
   `core-casmarts/data/authentik/custom-templates/if/flow.html`. Authentik lo sirve para TODOS los
   flows tipo SPA (login, cambio de contraseña, MFA). No es estático de verdad: tiene JS con
   `API_BASE = '/lm'` hardcodeado que hace `fetch()` en vivo a
   `/api/v1/public/theme/{flow_slug}?app={client_id}` (vía el gateway, prefijo `/lm/`) en cada
   carga de página, con Valkey de caché del lado del backend. Guardar un tema en el panel admin
   **no** regenera ningún archivo — el cambio se ve en el siguiente request porque se lee fresco
   (o se invalida la caché de Valkey al guardar).
2. **El endpoint `POST /{flow_slug}/deploy`** (existe en **ambos** backends — `admin.py` de Manager
   Y de Designer, cada uno con su propio `_build_universal_template()` / `login.html.j2`) escribe
   una versión server-renderizada de ese mismo contenido al **mismo path físico**
   (`/shared/authentik/templates/if/flow.html`, el mismo volumen montado en los dos contenedores).
   **Esto es una colisión real, no un aislamiento**: si alguien le da "Guardar y Aplicar" desde
   Designer después de que Manager desplegó el suyo, pisa la versión de Manager (y viceversa). Al
   momento de escribir esto, ambas copias de `login.html.j2` (Manager y Designer) tienen el mismo
   `API_BASE = '/lm'` hardcodeado — es decir, incluso lo que Designer despliega sigue llamando a la
   API de **Manager**, nunca a la propia. Si vas a tocar el flujo de `/deploy` de cualquiera de los
   dos, ten esto en cuenta antes de asumir que son independientes.
3. **`custom_authentik.js`** (en el `gateway`, nginx, inyectado vía `sub_filter` en **todas** las
   páginas de Authentik, no solo las de error): pensado originalmente para páginas SSR que ni
   Manager ni Designer tocan (ej. "Permiso denegado"), pero al inyectarse globalmente también corre
   dentro del shadow DOM de `flow.html` — y eso causó una colisión real el 2026-11-03 (botón de
   mostrar/ocultar contraseña con fondo e ícono invisibles: las reglas `!important` de
   `custom_authentik.js` ganaban la cascada sobre las de `flow.html`). Ya está parchado con un guard
   explícito (`if (document.getElementById('cs-screen')) return;` en `applyDynamicStyles()`/`tick()`)
   pero es una señal de que estos "motores" **no están tan aislados como parecen** — cualquier
   cambio a `custom_authentik.js` debe probarse también dentro de una pantalla `flow.html`, no solo
   en una página de error.
4. **`login.html.j2`** (en cada backend) es la plantilla Jinja2 que alimenta el `/deploy` de cada
   backend (punto 2) — no es un cuarto motor independiente, es la fuente de los dos `/deploy`.

**Antes de dar por cerrado un cambio de branding/CSS**: prueba una pantalla normal de login
(`flow.html`), una de error (ej. acceso denegado, `custom_authentik.js`), y — si vas a usar el botón
"Guardar y Aplicar" de Manager o Designer — confirma con quién editó el tema por última vez antes de
desplegar, para no pisar un cambio reciente del otro panel.

### 1.3.1 Los tres caminos por los que Login Manager toca a Authentik (y sus niveles de riesgo)

Esto importa si vas a tocar cualquier integración con Authentik, o a replicar este patrón para otro
sistema. Login Manager no es "un panel que guarda cosas en su base y ya" — toca a Authentik por tres
caminos independientes, con riesgo muy distinto cada uno (fuente: `docs/LOGIN_MANAGER_GUIA_TECNICA.html`):

| Camino | Qué hace | Riesgo |
|---|---|---|
| **SQL directo** — un segundo engine de SQLAlchemy apunta a la base `authentik` (mismo Postgres, cambiando el nombre de la base en el `DATABASE_URL`) | Lee `authentik_core_application`, `authentik_core_group`, `authentik_brands_brand` (resolver `client_id`→slug, listar apps, auto-enlazar por grupo, sincronizar Brands); **escribe** `authentik_providers_oauth2_scopemapping` (descripciones de scope) | **El más frágil de los tres.** Sin pasar por la API/ORM de Authentik — una migración interna de Authentik que renombre una columna/tabla rompe esto en producción sin ningún aviso de "API deprecada". Usar solo para lecturas de datos estables; evitar escrituras directas si existe alternativa por API. |
| **REST API con token** (`AUTHENTIK_API_TOKEN` + `httpx`) | Favicon→Brand nativo, sync de `PasswordPolicy`/`ReputationPolicy`/`PasswordExpiryPolicy`, alta de Brand+grupos vía blueprints | El camino "correcto". Todas estas funciones están diseñadas para **fallar "suave"**: si Authentik no responde, el cambio se guarda igual en la base local y se devuelve `(ok=False, error=...)` como advertencia — nunca se pierde el trabajo del administrador por una caída momentánea de Authentik. |
| **Webhook entrante** (`POST /api/v1/authentik-event`, secreto compartido en `X-Webhook-Secret`) | Authentik dispara un evento real (alta, login fallido, cambio de contraseña…) → Login Manager elige la plantilla de correo y la envía | Único camino en sentido inverso. El secreto se compara con `secrets.compare_digest` (nunca `==`, evita timing attacks). |

### 1.3.2 Reglas de CSS/responsividad para `flow.html` (4 incidentes reales, no teoría)

Fuente: `docs/LOGIN_MANAGER_GUIA_TECNICA.html` §06-07 y `docs/REPORTE_MEJORAS_UI_AUTHENTIK.md`. Estas
reglas existen porque ya se rompieron en producción, cada una más de una vez:

- **Nunca ocultar `<p>` genéricos** para limpiar texto redundante (`p:not(.clase){display:none}`) —
  el mensaje real de error ("contraseña incorrecta") también es un `<p>`, y una regla así de amplia
  se lo come. Excluye siempre clases de error/alerta explícitamente.
- **Nunca enumerar pantallas fijas** (`ak-stage-identification, ak-stage-password…`) — la siguiente
  pantalla nueva que Authentik agregue queda sin marca. Usa selectores por prefijo (`[class^="ak-"]`).
- **Los breakpoints reales son 920px y 480px, no 768px** — deliberadamente distinto del "estándar"
  de frameworks como Tailwind/Bootstrap: una laptop de 1366px con escalado de Windows al 200%
  reporta un viewport efectivo de ~683px y cae en la regla "móvil" sin ser un teléfono, ocultando la
  columna de logos en escritorio real. Prueba siempre a 1366×768 con zoom/escalado 150-200%.
- **`body` usa `overflow: auto`, nunca `hidden`**, a propósito — si la altura visible real es menor
  que los 560px de la tarjeta de login (barra del navegador + taskbar de por medio), sin el scroll
  el botón de "Iniciar sesión" queda inalcanzable.
- **Prueba siempre un login que falla** (contraseña incorrecta), no solo el camino feliz — es la
  única forma de confirmar que el mensaje de error sigue siendo visible después de un cambio.
- Si algo queda oculto y ninguna regla CSS lo trae de vuelta: busca JS poniendo
  `style.display = 'none'` con `!important` directo en el elemento — eso le gana a cualquier hoja de
  estilos, no importa cuántas reglas se agreguen encima.
- Si editas `custom_authentik.js`: sube el número de versión en `?v=` dentro de
  `gateway/sites-enabled/subdomains.conf` y `nginx -s reload` — si no, el navegador sigue usando la
  copia vieja en caché.

### 1.4 El estándar de auditoría CASMART (aplica a toda tabla transaccional)

Todas las tablas de negocio (en `authentik_login_manager`, tanto de Manager como de Designer) siguen
el mismo estándar: columnas canónicas (`id` UUIDv7, `ref`, `activo`, `borrado`, `row_version`,
`fecha_creacion`, `fecha_modificacion`, `usuario_creacion`, `usuario_modificacion`) pobladas por
triggers `audit_biu`/`audit_aiud`, con una bitácora de solo-inserción (`auditoria.log_auditoria`,
JSONB + hash SHA-256 encadenado) que permite detectar si algún registro fue alterado por fuera de la
aplicación. Ver `rules/postgres/rules.md` y `rules/centinela/rules.md` del kit CASMARTS, y
`docs/SECURITY_AUDIT_2026-11-04.md` de este repo para el detalle de cómo se verificó.

---

## 2. `authentik-login-manager` — guía de relevo para quien continúe el proyecto

Esta sección es para ti si vas a tomar este proyecto de aquí en adelante. Cubre qué hace, cómo está
armado por dentro, qué se corrigió en la ronda de trabajo de 2026-11, y qué queda pendiente —
para que puedas seguir mejorándolo sin tener que releer todo el código primero.

### 2.1 Qué es, en una frase

Un panel de administración (backend FastAPI + frontend React) que le permite a un administrador
diseñar visualmente el tema de login de Authentik (colores, logos, fondo, tipografías, mensajes,
plantillas de correo) **por tenant y por flow/app**, y lo expone a través de una API pública que
`flow.html` (la plantilla SPA de Authentik, ver §1.3) consulta en vivo en cada carga de página —
guardar un tema en el panel no "publica" nada, el cambio se ve en el siguiente request.

### 2.2 Stack técnico

| Capa | Tecnología | Versión (post auditoría 2026-11-04) |
|---|---|---|
| Backend | FastAPI + SQLAlchemy 2.x (async, `asyncpg`) + Alembic | Python 3.12.16, FastAPI 0.136.1, SQLAlchemy 2.0.28 |
| Caché/sesión | Valkey (compatible Redis) vía `redis` lib | redis-py 5.0.3 |
| Frontend | React 18 + Vite + TailwindCSS + TipTap (editor de correos) | React 18.3.1, Vite 5.4.21 (build-only), TipTap 3.32.2 |
| Base de datos | PostgreSQL 18.6, esquema `app` (+ `auditoria`, `public`) | Compartida con `authentik-login-designer` — ver §2.3 |
| Contenedores | `node:20.20.2-alpine` (build) + `nginx:1.31.8-alpine` (runtime) / `python:3.12.16-slim` | Pinneados a versión exacta desde 2026-11-04 |

### 2.3 El hecho más importante para entender esta arquitectura

**`authentik-login-manager` y `authentik-login-designer` NO son dos sistemas con sus propias bases
de datos — comparten la MISMA base física** (`authentik_login_manager` en `db-primary`), confirmado
por el `DATABASE_URL` de ambos `.env`. Las 5 tablas (`tenants`, `tenant_themes`,
`tenant_applications`, `tenant_email_bodies`, `password_policies`) viven en el esquema `app` de esa
base única. Esto significa:
- Un cambio de esquema (migración) hecho desde cualquiera de los dos repos afecta al otro — por eso
  la migración `026_schema_jsonb_uuidv7_comments.py` (ver `backend/alembic/versions/`) actualizó los
  modelos SQLAlchemy de AMBOS repos a la vez, no solo uno.
- Una fila que crees desde Designer es visible desde Manager, y viceversa — útil para probar, pero
  peligroso si pruebas contra datos reales de un tenant en producción sin confirmar primero.
- Designer es **single-tenant por diseño** (usa un `DEFAULT_TENANT_ID` fijo, no resuelve tenant por
  dominio) mientras Manager es multi-tenant real (resuelve por `Tenant.domain_pattern`, ver §2.4).
  Esta asimetría es intencional, no un bug — hay un plan detallado de paridad Designer↔Manager
  (pregunta al equipo/revisa los planes de trabajo guardados) que documenta, campo por campo y
  endpoint por endpoint, qué le falta a Designer para alcanzar a Manager, y qué partes de Manager NO
  se deben portar porque romperían la decisión single-tenant de Designer.

### 2.4 Conceptos de dominio (los modelos, y qué resuelve cada uno)

| Modelo | Qué representa |
|---|---|
| `Tenant` (`models/tenant.py`) | Una marca/organización — tiene `domain_pattern` (ej. `*.ca-smarts.com`) usado para resolver qué tenant corresponde a un hostname entrante. |
| `TenantTheme` (`models/tenant_theme.py`) | El tema visual de login de un `(tenant, authentik_flow_slug, authentik_app_slug?)` — colores, fondo, logos, tipografías (`font_heading`/`font_body`, con soporte de fuentes propias con licencia vía base64), textos, qué elementos se muestran. Es, por mucho, la tabla más grande (más de 40 columnas). |
| `TenantApplication` (`models/tenant_application.py`) | Enlace explícito `(tenant_id, application_slug)` — de qué tenant es cada Application de Authentik. Reemplazó un filtro por substring de nombre, frágil y ya con bugs reales. |
| `TenantEmailBody` (`models/email_body.py`) | Plantilla HTML de correo por `(tenant_id, flow_slug, event_type)` — 13 tipos de evento soportados (`password_reset`, `new_account`, `account_lockout`, etc.), ver `EMAIL_EVENT_TYPES`. |
| `PasswordPolicy` (`models/password_policy.py`) | Fila única (singleton, `SINGLETON_ID` fijo) — Authentik solo tiene una política de contraseña global hoy, no por tenant. Se sincroniza con 3 objetos reales de Authentik: `PasswordPolicy`, `ReputationPolicy` (bloqueo por intentos fallidos) y `PasswordExpiryPolicy`. |

**Resolución de tenant por dominio** (`utils/tenant.py`): dado un hostname, busca en Valkey (caché
1h) → si no está, recorre los `Tenant` activos y compara contra `domain_pattern` (soporta match
exacto, wildcard `*.dominio.com`, o regex) → si ninguno coincide, usa el tenant por defecto
(`DEFAULT_TENANT_UUID`, hardcodeado en ese archivo). El header `X-Tenant-Domain` es cómo el gateway
le pasa el hostname real al backend.

### 2.5 Mapa de endpoints (routers/)

| Router | Prefijo | Qué hace |
|---|---|---|
| `admin.py` | `/api/v1/themes` (vía `router`) | CRUD de temas, `/deploy` (escribe `flow.html` en el volumen compartido — ver colisión en §1.3), font presets, favicon→Brand de Authentik, descubrimiento de Applications de Authentik, descarga de blueprint, las 3 integraciones de §1.3.1 |
| `tenant.py` | `/api/v1/tenant` | Resolución de tenant (`/resolve`, `/list`), ajustes de marca (`/settings`), apps enlazadas (`/applications`) |
| `public.py` | `/api/v1/public` (prefijo real `/lm/api/v1/public/...` detrás del gateway) | Endpoints SIN autenticación — es lo que `flow.html` consulta EN VIVO en cada carga de página (ver §1.3), no un archivo ya desplegado |
| `password_policy.py` | — | CRUD de la política + sincronización real con las 3 policies de Authentik mencionadas en §2.4 |
| `authentik_events.py` | `/api/v1/authentik-event` | Webhook receptor — Authentik llama aquí en cada evento real (alta, login fallido, etc.), dispara el envío de correo correspondiente |
| `email_sync.py` | — | Sincroniza/despliega plantillas de email hacia Authentik |
| `auth.py` | — | Login/logout del panel admin mismo (sesión del propio Login Manager, no de los usuarios finales) |

Todos los endpoints de escritura (admin.py, tenant.py, password_policy.py) requieren
`X-Admin-Key` — ver `ADMIN_API_KEY` en `.env` — excepto `public.py`, que es deliberadamente público
(lo consume el HTML ya desplegado, sin sesión).

### 2.6 Qué se hizo en esta ronda de trabajo (2026-11-03/04) — para que no se repita el diagnóstico

Ver `docs/SECURITY_AUDIT_2026-11-04.md` (este repo) para el detalle completo con
hallazgo→severidad→corrección. Resumen de lo relevante para seguir desarrollando:

- **Rol de base de datos acotado**: dejó de conectarse como el superusuario `admin` (el mismo que
  usa Authentik) — ahora usa `theme_app_user`, con `search_path = app, public` y solo los permisos
  que necesita. Si agregas una tabla nueva, acuérdate de dar `GRANT` explícito a ese rol (el esquema
  `app` NO tiene `GRANT USAGE ... TO PUBLIC` por omisión, a diferencia de `public`).
- **PKs a UUIDv7**: todas las tablas usan `server_default=text("uuidv7()")` en el modelo (no
  `default=uuid.uuid4` de Python) — si agregas una tabla nueva, sigue ese mismo patrón o SQLAlchemy
  lanzará `FlushError` al no saber que debe pedir el id generado de vuelta vía `RETURNING`.
  Ver el comentario en `models/tenant_application.py`.
  **Trampa a evitar**: tanto el `server_default` del modelo ORM como el `DEFAULT uuidv7()` real a
  nivel de columna en Postgres deben existir — uno sin el otro no es suficiente.
- **JSON → JSONB**: `tenants.config`, `tenant_themes.custom_messages`, `tenant_themes.expansion_config`.
- **CVEs reales corregidos** (no solo "versión vieja" — cada uno verificado contra la base de datos
  de vulnerabilidades OSV, no asumido):
  - Backend: `jinja2` 3.1.3→3.1.6, `python-multipart` 0.0.9→0.0.33, `bleach` 6.1.0→6.4.0 (el
    sanitizador real de `custom_messages`, verificado que sigue bloqueando `<script>` tras el bump).
  - Frontend: `dompurify` 3.0.9→3.4.17 (23 CVEs de bypass de sanitización/XSS — es el sanitizador de
    HTML del lado cliente), `@tiptap/*` 3.27.1→3.32.2 (2 CVEs: contaminación de prototipo vía
    `mergeAttributes()`, y ReDoS al parsear markdown).
  - Imágenes base: `node:18-alpine` (EOL desde abril 2025) → `node:20.20.2-alpine`,
    `nginx:alpine`/`python:3.12-slim` (flotantes) → pineados a versión exacta
    (`nginx:1.31.8-alpine`, `python:3.12.16-slim`).
- **Desplegado y verificado en vivo**: ambas imágenes reconstruidas, contenedores
  `casmarts-login-backend`/`casmarts-login-frontend` recreados, `/health` responde `healthy`,
  versiones confirmadas dentro del contenedor corriendo (no solo en el Dockerfile).

### 2.7 Lo que NO se tocó — y por qué (para que lo retomes con contexto, no desde cero)

- **Vite sigue en la rama 5.x** (dev-server tiene 8 CVEs conocidos, todos de exposición del servidor
  `vite dev` — rutas cruzando `server.fs.allow`, ejecución de script cross-origin vía middleware).
  Arreglarlos requiere saltar a Vite 8.x (3 versiones mayores, con cambios de ruptura confirmados por
  el propio `npm audit`). Como este contenedor SOLO corre `vite build` en producción (nunca el
  dev-server), el riesgo real es bajo — se documentó en vez de forzar un salto sin poder probarlo a
  fondo. Si decides hacerlo, plan: fijar todo `@tiptap/*` a la MISMA versión exacta primero (ya se
  topó un conflicto real de peer-dependencies entre `extension-color` y `extension-text-style` al no
  hacerlo así), y probar visualmente el editor de correos (TipTap) después del bump.
- **16 hallazgos moderados de `npm audit` en `@angular/cli`** (del lado de Designer) no aplican a
  Manager — Manager usa Vite/CRA-style tooling, no Angular CLI.
- **Vault no se integró** — Manager sigue leyendo credenciales de `.env` (ver §1.2). Es un cambio
  arquitectónico real (no un fix de una tarde), documentado como pendiente en
  `docs/SECURITY_AUDIT_2026-11-04.md` fila "Vault provisionado pero los backends ... no leen secretos
  de ahí". Si te toca hacerlo: la Fase 1 natural sería mover `ADMIN_API_KEY`, `SESSION_SECRET`,
  `AUTHENTIK_API_TOKEN` y `AUTHENTIK_WEBHOOK_SECRET` a `secret/casmarts/login-manager/prod` y
  leerlos en el `entrypoint`/`lifespan` de `main.py` en vez del `.env` — sin tocar el resto de la
  app. Pide al equipo de infraestructura la guía interna de Vault para el paso a paso detallado.
- **`React` sigue en 18.x** — no se evaluó un salto a React 19 esta ronda (no hay CVEs reales que lo
  justifiquen hoy; es una mejora de mantenimiento a futuro, no de seguridad).
- **Paridad funcional Designer↔Manager** (ver §2.3) — Manager ya tiene todo lo descrito en §2.4-2.5;
  es Designer el que va atrás. No es trabajo pendiente de ESTE repo, pero es contexto útil si alguna
  vez te piden "que Designer haga lo mismo que Manager".

### 2.8 Cómo levantarlo / desarrollarlo

```bash
cd authentik-login-manager
cp .env.example .env   # luego edita — OJO: .env.example tiene POSTGRES_HOST=casmarts-core-pgpool,
                       # un alias que NO existe hoy; el valor real en el .env que SÍ corre es
                       # POSTGRES_HOST=db-primary (nombre del servicio en identity-network)
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose logs -f backend frontend   # para ver arranque/errores
```

El frontend expone `3080:3000` (puerto host:contenedor, ver `compose.yml`) — panel en
`http://10.4.3.208:3080` desde la red interna. El backend no publica puerto al host (`#ports:`
comentado en `compose.yml`) — solo es alcanzable por el frontend y por Authentik dentro de
`identity-network`/`aura-network`.

**Para probar un cambio de código sin reconstruir la imagen**: el `compose.yml` monta
`./backend:/app` como volumen y el `CMD` del backend corre con `--reload` — basta guardar el
archivo y Uvicorn recarga solo. El frontend (`Dockerfile` multi-stage, build estático servido por
nginx) **sí necesita rebuild** (`docker compose build frontend && docker compose up -d frontend`)
para ver un cambio, no tiene modo dev montado en este `compose.yml`.

### 2.9 Dónde seguir leyendo

- `docs/LOGIN_MANAGER_GUIA_TECNICA.html` (este repo, 29-oct-2026) — la fuente más detallada sobre
  los 3 caminos de integración con Authentik (§1.3.1) y las reglas de CSS/responsividad (§1.3.2).
  Se mantiene como "documento vivo" — si la arquitectura cambia otra vez, hay que actualizarlo junto
  con el código, no después (su propia instrucción, al final del archivo).
- `docs/REPORTE_MEJORAS_UI_AUTHENTIK.md` (este repo) — bitácora de cada bug visual de Authentik ya
  encontrado y corregido, con su addendum 2026-11-03 sobre la colisión de `custom_authentik.js` en
  el shadow DOM de `flow.html` (ver §1.3).
- `docs/ADVANCED_API_CUSTOMIZATION_GUIDE.md` y `docs/EMAIL_SYNC_GUIDE.md` (este repo) — para quien
  vaya a integrar un cliente externo contra la API de temas/correo, o sincronizar plantillas de
  email manualmente.
- `README.md` (este repo) — útil para requisitos y primer arranque; para el mecanismo real de
  servido del tema (`flow.html` en vivo, no HTML estático), usa §1.3 de este documento.
- `docs/SECURITY_AUDIT_2026-11-04.md` (este repo) — auditoría completa con hallazgo→severidad→
  corrección, incluyendo lo que sigue pendiente y por qué. `SECURITY_AUDIT_2026-07.md` es la ronda
  anterior, ya superada por esta — queda como referencia histórica.
- §1 de este documento — arquitectura del ecosistema completo (dónde embona este proyecto en el resto).
- Guía interna de Vault (no versionada en git, pídela al equipo de infraestructura) — si decides
  cerrar el pendiente de §2.7 sobre integrar Vault.

---

## 3. `authentik-login-designer` — notas de relevo

Designer resuelve el mismo problema que Manager (temas visuales de login de Authentik) pero con una
decisión de diseño distinta y deliberada: **es single-tenant**. No intentes "corregirlo" a
multi-tenant sin antes leer el porqué — está documentado en su propio código
(`routers/tenant.py`/`config.py`) como una decisión explícita: replicar la resolución de tenant por
header que usa Manager "sería seguridad aparente sin sustento real" en este backend. Usa un
`DEFAULT_TENANT_ID` fijo en vez de resolver por dominio.

> **Importante, ver §1.3**: el `POST /{flow_slug}/deploy` de este repo escribe al MISMO archivo
> físico (`flow.html`) que el de Manager — no son pipelines aislados, es una colisión real de
> último-en-escribir-gana. Además, la copia de `login.html.j2` de ESTE repo tiene, al momento de
> escribir esto, `API_BASE = '/lm'` hardcodeado — es decir, si Designer despliega, el HTML
> resultante sigue llamando a la API pública de **Manager**, no a la propia. Si vas a usar o
> arreglar el `/deploy` de Designer, confirma primero si eso es intencional (¿Designer depende a
> propósito de los datos de Manager para ese tenant?) o es simplemente una copia desactualizada que
> nadie ajustó — no está documentado cuál de las dos es.

### 3.1 Stack técnico

| Capa | Tecnología | Versión (post auditoría 2026-11-04) |
|---|---|---|
| Backend | FastAPI + SQLAlchemy 2.x (async) + Alembic | Comparte `requirements.txt` con Manager (mismas versiones, ver §2.2) |
| Frontend | Angular 21 (standalone + signals) + TailwindCSS + PrimeNG-style + TipTap | Angular 21.2.26, TipTap 3.32.2 |
| Base de datos | **La misma base física que Manager** (`authentik_login_manager`, esquema `app`) | Ver §2.3 — no tiene BD propia |
| Contenedores | `node:22-alpine` (build) + `nginx:alpine` (runtime) | Nota: a diferencia de Manager, estos dos siguen en tag flotante — pendiente pinear si se quiere la misma disciplina (ver §3.3) |

### 3.2 Qué se hizo en esta ronda de trabajo (2026-11-03/04)

Mismo tipo de correcciones que en Manager, aplicadas en paralelo porque Designer comparte la base de
datos y varias dependencias de frontend con Manager:
- Mismo fix de esquema/UUIDv7/JSONB que Manager (es la misma migración, una sola base — ver §2.6).
- Mismos CVEs de backend (`jinja2`, `python-multipart`, `bleach`).
- `dompurify` 3.0.9→3.4.17 y `@tiptap/*` 3.27.1→3.32.2 — mismos CVEs que Manager (ver §2.6),
  corregidos por separado porque son `package.json` independientes.
- `@angular/*` 21.2.15→21.2.26 (2 CVEs de XSS reales) y arreglo de dos bugs de empaquetado de
  terceros no relacionados con la versión de Angular: `@tiptap/extension-mention` y
  `@tiptap/suggestion` no declaran correctamente sus propias dependencias (`@tiptap/suggestion` y
  `@floating-ui/dom` respectivamente) — se agregaron como dependencias directas explícitas.
- `angular.json`: presupuesto de bundle (`budgets`) subido de 500kB/1MB a 700kB/1.5MB — el bundle
  real pesa ~1MB y bloqueaba el build de producción por omisión.
- **Nota de troubleshooting para la próxima vez**: regenerar el lockfile de este repo con el npm
  10.x que trae `node:22-alpine` por defecto puede fallar con un error interno de npm
  (`Cannot read properties of null (reading 'edgesOut')`, bug conocido de arborist con este grafo de
  dependencias). Se resolvió instalando `npm@11.13.0` (la versión que el propio `package.json`
  declara en `packageManager`) antes de correr `npm install` — no hace falta `--legacy-peer-deps` si
  usas esa versión de npm.

### 3.3 Lo que NO se tocó — y por qué

- **`node:22-alpine` y `nginx:alpine` en `frontend/Dockerfile` siguen en tag flotante** (a diferencia
  de Manager, que ya se pineó a versión exacta esta ronda) — pendiente, mismo criterio que Manager
  si se retoma: pinear a una versión exacta conocida-buena.
- **16 hallazgos moderados de `npm audit`** están todos dentro de la cadena de herramientas interna
  de `@angular/cli` (`glob`/`minimatch`/`pacote`/`sigstore`, usados por `ng` para cosas como
  `ng add`/`ng update`) — nunca se empaquetan en el bundle servido, arreglarlos requiere Angular CLI
  v22 (otro salto mayor, no evaluado esta ronda).
- **Paridad funcional con Manager** (fuentes, favicon→Brand, `tenant_applications`, webhooks de
  eventos reales, sync de lockout con Authentik) — Designer va atrás de Manager en features, de
  forma intencional hasta ahora (ver §2.3). Hay un plan de trabajo detallado para cerrar esa brecha
  campo por campo si se decide hacerlo — pregunta al equipo por "el plan de paridad Designer↔Manager".

### 3.4 Dónde seguir leyendo

- `docs/SECURITY_AUDIT_2026-11-04.md` (este repo) — auditoría completa.
- `docs/ADVANCED_API_CUSTOMIZATION_GUIDE.md` (este repo) — personalización avanzada de la API.
- `authentik-login-manager/docs/LOGIN_MANAGER_GUIA_TECNICA.html` y
  `.../REPORTE_MEJORAS_UI_AUTHENTIK.md` — viven solo en el repo de Manager, pero describen
  `flow.html`, que es EL MISMO archivo que este repo también despliega (ver §3, nota de arriba) —
  léelos si vas a tocar el `/deploy` de Designer o el CSS de `flow.html` desde este lado.
- §1-2 de este documento — arquitectura del ecosistema y el detalle completo de Manager (aplica en
  gran parte a Designer también, por la base de datos y el archivo `flow.html` compartidos).
