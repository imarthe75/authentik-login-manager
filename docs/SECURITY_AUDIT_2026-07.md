# Auditoría de Seguridad — Login Manager
**Fecha:** 2026-07-01 · **Alcance:** `authentik-login-manager/` (backend FastAPI + frontend React) · **Método:** Revisión estática de código + pruebas API en vivo (sin acceso de navegador/capturas)

---

## 🔴 Cadena de ataque crítica (resumen ejecutivo)

```
RichTextEditor (modo HTML, sin sanitizar)
        ↓
body_html guardado en TenantEmailBody
        ↓
Renderizado en 3 iframes SIN sandbox (EmailEditorSplit, TemplateGallery, EmailPreview)
        ↓
EmailPreview.tsx además interpola sin DOMPurify (buildLiveHtml)
        ↓
Iframe sin sandbox = mismo origen → script puede leer bundle JS servido
        ↓
VITE_ADMIN_KEY está baked literal en el bundle (Vite expone todo VITE_*)
        ↓
ADMIN_API_KEY es GLOBAL (no por tenant) + X-Tenant-Domain lo controla el cliente
        ↓
Compromiso de CUALQUIER tenant: leer/editar/borrar temas, desplegar HTML
malicioso en la página de login real (auth.casmart.internal)
```

---

## Hallazgos por categoría

### STRIDE

| Amenaza | Hallazgo | Severidad |
|---|---|---|
| **Spoofing** | `X-Tenant-Domain` / `X-Forwarded-Host` controlados por cliente, sin validar contra proxy confiable (`admin.py:124-128`) | 🔴 Crítica |
| **Spoofing** | `ADMIN_API_KEY` global compartida entre tenants, expuesta en bundle frontend | 🔴 Crítica |
| **Tampering** | `body_html` de emails sin sanitizar antes de render (XSS almacenado) | 🔴 Crítica |
| **Tampering** | Comparación de API key con `!=` (no constant-time) — `admin.py:44` | 🟠 Alta |
| **Repudiation** | Sin logging de intentos fallidos de `X-Admin-Key` | 🟡 Media |
| **Information Disclosure** | `err.message` del backend expuesto directo en UI (TenantSelector, AccessAndNotificationsTab, useTheme) | 🟠 Alta |
| **Information Disclosure** | `GET /api/v1/emails/export/{event_type}` sin autenticación — filtra plantillas completas | 🔴 Crítica |
| **Denial of Service** | Sin rate limiting en ningún endpoint (fuerza bruta de `X-Admin-Key` viable) | 🟠 Alta |
| **Elevation of Privilege** | Cadena XSS → extracción de admin key → API completa | 🔴 Crítica |

### OWASP Top 10 (2021) — Web

- **A01 Broken Access Control**: endpoints `email_sync.py` (`/export`, `/sync-to-authentik`) sin guard; `/public/theme/invalidate-cache` público (DoS de caché).
- **A03 Injection**: inyección de cabeceras SMTP vía `subject`/`to_email` sin filtrar `\r\n` (`admin.py:491-493`).
- **A05 Security Misconfiguration**: CORS con `allow_credentials=True`; Dockerfiles corren como root; `--reload`/`npm run dev` en imagen que podría llegar a producción.
- **A07 Identification and Authentication Failures**: comparación no constante de API key; sin rate limiting; secreto único global sin rotación ni expiración.
- **A08 Software and Data Integrity Failures**: `dangerouslySetInnerHTML`/iframes sin sandbox permiten ejecución de contenido no confiable con el mismo origen que la app admin.

### OWASP API Security Top 10

- **API1 Broken Object Level Authorization**: `X-Tenant-Domain` спoofing permite acceder a datos de otro tenant sin autorización por-recurso.
- **API2 Broken Authentication**: single shared secret sin distinción de identidad/rol, expuesto en cliente.
- **API3 Broken Object Property Level Authorization**: sin validación de tamaño/longitud en varios campos (`system_name`, `body_html`).
- **API8 Security Misconfiguration**: endpoints de `email_sync.py` sin autenticación.
- **API9 Improper Inventory Management**: routers `email_sync` y `tenant` no documentados como públicos intencionalmente vs. descuido — sin diferenciación clara en el código.

### NIST Cybersecurity Framework

- **Identify**: sin inventario formal de qué endpoints son públicos por diseño vs. por omisión.
- **Protect**: control de acceso insuficiente (API key global, sin RBAC por tenant); dependencias desactualizadas (Starlette 0.36.3, vulnerable a CVE-2026-48710).
- **Detect**: sin logging de intentos de autenticación fallidos, sin alertas.
- **Respond/Recover**: sin runbook de rotación de secretos ante fuga (confirmada: SMTP password real en historial git).

### Data Protection (PII / GDPR / LFPDPPP)

- El SMTP real (`<correo-corporativo-redactado>` + app password) quedó en el **historial de git** (commit `93700f1`) — dato de acceso a cuenta de correo corporativa expuesto de forma persistente en el repositorio.
- `body_html` de correos puede contener PII de usuarios (nombres, emails) sin controles de retención/anonimización documentados.
- Sin política de minimización: `log.error` puede volcar excepciones completas que incluyan fragmentos de datos sensibles.

### Infrastructure Security

- Contenedores backend y frontend corren como **root** (sin `USER` en Dockerfile).
- `compose.yml` monta el código fuente completo como volumen (`./backend:/app`) — válido en dev, riesgoso si el mismo compose llega a producción.
- Backend corre con `--reload` (Uvicorn dev mode) — no apto para producción (recarga de código, más superficie de depuración expuesta).

### Supply Chain & Dependencies

- **Starlette 0.36.3** — vulnerable a **CVE-2026-48710 "BadHost"** (bypass de controles de acceso vía Host header malformado), corregido en 1.0.1. FastAPI 0.110.0 lo fija indirectamente.
- Dependencias backend con versión exacta (`==`) — bueno para reproducibilidad, pero sin proceso visible de actualización/auditoría (no hay `pip-audit`/Dependabot detectado).
- Frontend con lockfile presente (`package-lock.json`) — correcto.

### SDLC Security

- `.gitignore` no cubre `*.key`, `*.pem`, `.env.*.local` — solo `.env` genérico.
- Secretos reales llegaron a un commit antes de excluir `.env` — indica que el flujo de desarrollo permitió commitear secretos al menos una vez.
- Sin CI/CD visible que ejecute SAST/dependency scanning antes de build.

### Compliance

- Falta de segregación de secretos por entorno (mismo `ADMIN_API_KEY` default hardcodeado en `compose.yml`, reutilizable en cualquier despliegue que no lo sobreescriba).
- Sin evidencia de cifrado en reposo para `body_html`/logos en base64 almacenados en Postgres (no necesariamente requerido, pero a documentar si aplica LFPDPPP a los datos que fluyen por los templates).

---

## Hallazgos de QA Funcional (heurísticas de negocio)

- **Validación insuficiente**: input de "correo de prueba" solo usa `type="email"` HTML5, sin validación programática ni límite de longitud.
- **Mensajes de error crudos**: varios flujos muestran `err.message` del backend directamente al usuario (fuga de detalles internos: nombres de tabla, rutas, etc.)
- **Sin `maxLength` en input de Subject** pese a mostrar contador "X/200" — el contador no se aplica realmente.
- **Fallback MIME inseguro**: si un base64 no matchea el patrón `data:image/...;base64,`, se asume `image/png` igual y se decodifica (`public.py`).

---

## Severidad y estado de remediación

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| 1 | Endpoints `email_sync.py` sin autenticación | 🔴 Crítica | ✅ Corregido |
| 2 | XSS almacenado vía `body_html` sin sanitizar + iframes sin sandbox | 🔴 Crítica | ✅ Corregido |
| 3 | `VITE_ADMIN_KEY` expuesta en bundle cliente | 🔴 Crítica | ⚠️ Mitigado (rompe la cadena de explotación vía fix #2), rediseño arquitectónico pendiente |
| 4 | Comparación no constant-time de API key | 🟠 Alta | ✅ Corregido |
| 5 | Sin rate limiting en autenticación admin | 🟠 Alta | ✅ Corregido |
| 6 | Inyección de cabeceras SMTP (CRLF) | 🟠 Alta | ✅ Corregido |
| 7 | Starlette 0.36.3 vulnerable a CVE-2026-48710 | 🟠 Alta | ✅ Corregido (actualizado) |
| 8 | `X-Tenant-Domain`/`X-Forwarded-Host` spoofing | 🟠 Alta | ✅ Corregido (ver detalle abajo) |
| 9 | CORS con credentials + orígenes por env sin validar wildcard | 🟡 Media | ✅ Corregido |
| 10 | Mensajes de error crudos expuestos al usuario | 🟡 Media | ✅ Corregido |
| 11 | Fallback MIME inseguro en decodificación base64 | 🟡 Media | ✅ Corregido |
| 12 | Sin `maxLength` real en Subject / `system_name` | 🟡 Media | ✅ Corregido |
| 13 | Dockerfiles corren como root | 🟡 Media | ✅ Corregido |
| 14 | SMTP password real en historial de git | 🔴 Crítica | ❌ **Requiere acción manual** (ver abajo) |
| 15 | `.gitignore` incompleto | 🟢 Baja | ✅ Corregido |
| 16 | Sin security headers (CSP, X-Frame-Options, etc.) | 🟡 Media | ✅ Corregido |

---

## Verificación post-fix (regresión)

Todos los fixes se probaron contra los contenedores reconstruidos y reiniciados:

- ✅ `tsc --noEmit` sin errores tras todos los cambios de frontend.
- ✅ `/health` responde `{"status":"healthy","cache":"connected"}`.
- ✅ Los 5 headers de seguridad presentes en respuestas HTTP (`X-Frame-Options`, `X-Content-Type-Options`, `CSP`, `Referrer-Policy`, `Permissions-Policy`).
- ✅ `email_sync.py` ahora exige `X-Admin-Key` (antes: público).
- ✅ Rate limiting confirmado: 20 intentos fallidos → HTTP 429 en el siguiente.
- ✅ Starlette actualizado 0.36.3 → **1.3.1** (resuelve CVE-2026-48710), FastAPI 0.136.1, pydantic 2.13.4 — sin romper compatibilidad.
- ✅ Los 5 previews de email siguen renderizando correctamente (HTTP 200, sin fugas de sintaxis Jinja) tras el upgrade de dependencias.
- ✅ Contenedores corren como usuario no-root (`app`/`node`, uid 1000).
- ⚠️ **Regresión detectada y corregida durante la verificación**: el cambio a usuario no-root inicialmente rompió `POST /deploy` (permiso denegado al escribir en el volumen compartido del host). Causa: el UID del contenedor no coincidía con el propietario (uid 1000) del directorio host montado. Fix: se fijó el UID/GID del usuario `app` a 1000 explícitamente en el Dockerfile. Re-verificado: `/deploy` vuelve a escribir `flow.html` correctamente.
- ℹ️ `npm audit` detectó 2 vulnerabilidades adicionales en dependencias de frontend, evaluadas y no corregidas por las razones siguientes:
  - `dompurify` (moderada, GHSA-vxr8-fq34-vvx9 / GHSA-cmwh-pvxp-8882): afecta el uso de `setConfig()` persistente y `RETURN_TRUSTED_TYPE` — **no aplica** a nuestro uso (llamada única `DOMPurify.sanitize(html, {...})` sin esas APIs). Sin parche disponible aún a la fecha. Monitorear.
  - `esbuild`/`vite` (moderada, GHSA-67mh-4wv8-2f99): permite a un sitio externo enviar requests al dev-server y leer la respuesta. Solo relevante mientras `vite dev` está corriendo (este contenedor lo hace). Requiere `vite@6` (breaking change) — no aplicado para evitar romper el toolchain sin coordinación previa; recomendado programar el upgrade por separado con pruebas de regresión del build.

---

## ⚠️ Acciones que requieren intervención manual (no puedo ejecutarlas)

1. **Rotar la contraseña de aplicación de Gmail** (`<correo-corporativo-redactado>`) — quedó expuesta en el historial de git (commit `93700f1`). Debe generarse una nueva App Password en la cuenta de Google y actualizar `.env`.
2. **Purgar el historial de git** de los commits que contienen `.env` con secretos reales (`git filter-repo` o BFG Repo-Cleaner) — es una operación destructiva/irreversible sobre el historial que requiere coordinación con el equipo (reescribe hashes, afecta a quien tenga el repo clonado) y posible force-push. No la ejecuto sin tu confirmación explícita.
3. **Rotar `ADMIN_API_KEY`** en producción tras el fix — el valor actual estuvo expuesto en el bundle del frontend; aunque el fix rompe la vía de explotación (XSS→lectura del bundle), el valor en sí ya pudo haber sido observado por cualquiera que abriera DevTools. Recomiendo generar uno nuevo y actualizar `.env` + reiniciar.
4. **Aislamiento de red entre servicios** (`identity-network`): el backend de login-manager comparte esa red Docker con Authentik, Vault, login-designer y otros servicios sin ningún tipo de segmentación — cualquier contenedor de esa red puede alcanzar `casmarts-login-backend:8000` directamente. El fix aplicado (`_is_trusted_proxy_peer`, ver abajo) cierra el vector de explotación concreto (spoofing de tenant), pero la falta de aislamiento de red en sí sigue siendo una superficie de ataque más amplia (ej. si otro servicio de esa red es comprometido, podría alcanzar el backend directamente para otros fines). Solucionarlo de raíz requiere segmentar la red Docker (ej. separar una red "datos" interna de una red "gateway"), un cambio que toca la topología de *todos* los servicios del ecosistema — no lo apliqué por su alcance y blast radius; requiere planificación y pruebas coordinadas con cada servicio.

### ✅ Fix aplicado: spoofing de `X-Tenant-Domain` / `X-Forwarded-Host`

Se implementó en dos capas, verificado contra el gateway real (`https://loginmanager.casmart.internal`) y contra acceso directo al contenedor (bypass del gateway):

1. **Gateway (control primario)** — `core-casmarts/gateway/sites-enabled/subdomains.conf`, bloque `/api/` de `loginmanager.casmart.internal`: se agregó `proxy_set_header X-Tenant-Domain $host;` y `proxy_set_header X-Forwarded-Host $host;`, sobrescribiendo cualquier valor que el cliente intente enviar con el dominio ya validado por nginx (SNI/Host matching). Recargado con `nginx -s reload` (sin downtime).
2. **Backend (defensa en profundidad)** — `_is_trusted_proxy_peer()` en `admin.py`: solo se confía en esos headers si la conexión TCP inmediata proviene del contenedor `casmarts-core-gateway` (resuelto por DNS de Docker en cada request, vía `TRUSTED_PROXY_HOST` en config). Si la petición llega desde cualquier otro origen (ej. otro contenedor de `identity-network` saltándose el gateway), los headers se ignoran y se cae al fallback seguro (`request.client.host`), con log de advertencia.

**Verificado:** spoofeando `X-Tenant-Domain: evil.attacker.com` tanto vía el gateway público como directo al contenedor (bypass), el resultado es idéntico a una petición sin spoofing — el header ya no tiene ningún efecto en ninguna de las dos rutas.
