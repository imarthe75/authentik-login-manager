# Guía de Sincronización de Plantillas de Email

## 📋 Visión General

El Login Manager controla todas las plantillas de email (password reset, account verification, etc.) y las sincroniza automáticamente con Authentik. Esto permite:

- **Diseño centralizado** en Login Manager
- **Sincronización automática** a Authentik
- **Branding consistente** en todos los emails
- **Fallback manual** si la sincronización automática falla

---

## 🔄 Flujo

```
1. Admin diseña/edita plantilla en Login Manager
                ↓
2. Guardada en tabla tenant_email_bodies (BD)
                ↓
3. Sincronización automática a Authentik
                ↓
4. Authentik usa plantilla en próximos emails
```

---

## 🚀 Métodos de Sincronización

### Método 1: API Endpoint (Automático)

**Exportar plantilla:**
```bash
curl http://loginmanager.casmart.internal:8000/api/v1/emails/export/password_reset | jq .
```

**Sincronizar a Authentik:**
```bash
curl -X POST \
  "http://loginmanager.casmart.internal:8000/api/v1/emails/sync-to-authentik?event_type=password_reset"
```

**Respuesta exitosa:**
```json
{
  "status": "synced",
  "event_type": "password_reset",
  "authentik_template": "authentik_core-password-reset",
  "tenant_id": "00000000-0000-0000-0000-000000000001"
}
```

---

### Método 2: Script Python (Batch - Todos los emails)

**Obtener token de Authentik:**
```bash
# Ir a: https://auth.casmart.internal/if/admin/
# → Account → API Tokens → Create → Copiar token
export AUTHENTIK_API_TOKEN="<token_aquí>"
export AUTHENTIK_HOST="http://auth.casmart.internal"
```

**Ejecutar sincronización:**
```bash
cd backend
python scripts/sync_emails_to_authentik.py
```

**Salida esperada:**
```
🔗 Conectando a Authentik: http://auth.casmart.internal
📧 Sincronizando 5 plantillas de email...

✅ account_lockout        → authentik_core-account-locked
✅ email_verification     → authentik_core-email-confirmation
✅ new_account            → authentik_core-user-created
✅ password_reset         → authentik_core-password-reset
✅ security_change        → authentik_core-security-alert

============================================================
✅ Synced: 5 | ❌ Failed: 0
============================================================
```

---

### Método 3: Manual (Fallback)

**Paso 1: Obtener token de Authentik**
```bash
# URL: https://auth.casmart.internal/if/admin/
# Clic en tu usuario (arriba derecha) → Account
# Buscar "API Tokens" → Create → Copiar token
```

**Paso 2: Descargar plantilla de Login Manager**
```bash
curl http://loginmanager.casmart.internal:8000/api/v1/emails/export/password_reset > email_template.json
cat email_template.json | jq .body_html > template.html
```

**Paso 3: Actualizar en Authentik manualmente**
```bash
# Opción A: Via API
AUTHENTIK_TOKEN="<token>"
curl -X PATCH \
  -H "Authorization: Bearer $AUTHENTIK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Restablecer contraseña",
    "html": "<html>...</html>"
  }' \
  http://auth.casmart.internal/api/v3/core/email_templates/authentik_core-password-reset/

# Opción B: Via UI (más fácil)
# 1. IR a https://auth.casmart.internal/if/admin/
# 2. System → Email Configuration → Email Templates
# 3. Buscar "Password Recovery"
# 4. Editar → Pegar HTML → Save
```

**Paso 4: Verificar que se aplicó**
```bash
# Enviar email de prueba
curl -X POST \
  -H "X-Tenant-Domain: casmart.internal" \
  -H "Content-Type: application/json" \
  -d '{
    "to_email": "tu@example.com",
    "event_type": "password_reset"
  }' \
  http://loginmanager.casmart.internal:8000/api/v1/themes/password-recovery/emails/test
  
# Verificar que email tiene logo, colores y nuevo contenido
```

---

## 📧 Plantillas Disponibles

| Event Type | Template Name | Descripción |
|---|---|---|
| `password_reset` | `authentik_core-password-reset` | Recuperación de contraseña |
| `email_verification` | `authentik_core-email-confirmation` | Verificación de email |
| `new_account` | `authentik_core-user-created` | Bienvenida nueva cuenta |
| `account_lockout` | `authentik_core-account-locked` | Alerta de bloqueo de cuenta |
| `security_change` | `authentik_core-security-alert` | Cambio de seguridad |

---

## 🔧 Configuración Requerida

**Variables de entorno (para sincronización automática):**

```bash
# .env del backend
AUTHENTIK_HOST=http://auth.casmart.internal
AUTHENTIK_API_TOKEN=<token_de_authentik>
```

**O via docker-compose.yml:**
```yaml
services:
  backend:
    environment:
      - AUTHENTIK_HOST=http://auth.casmart.internal
      - AUTHENTIK_API_TOKEN=${AUTHENTIK_API_TOKEN}
```

---

## ⚠️ Troubleshooting

| Problema | Causa | Solución |
|---|---|---|
| 401 Unauthorized | Token inválido o expirado | Generar nuevo token en Authentik Admin |
| 404 Template not found | Template no existe en Authentik | Verificar nombre de template en tabla AUTHENTIK_TEMPLATE_MAP |
| Timeout | Authentik no responde | Verificar que auth.casmart.internal es accesible |
| HTML no aparece en email | Body_html está vacío en BD | Verificar que template se guardó correctamente en Login Manager |
| Colores no se aplican | CSS inline no es válido | Revisar HTML en template, usar estilos inline <style> |

---

## 📝 Ejemplo: Agregar logo a plantilla

**En Login Manager Admin UI:**
1. Ir a tema → Tab Emails
2. Editar "password_reset"
3. En "Cuerpo del correo" agregar:
```html
<div style="text-align: center; margin-bottom: 20px;">
  <img src="[[ logo_base64 ]]" alt="CASMARTS" style="max-width: 200px;">
</div>
```
4. Guardar
5. Ejecutar sincronización
6. Próximos emails mostrarán el logo

---

## 🔐 Obtener Token de Authentik

**Opción 1: Via UI (Recomendado)**
```
1. Ir a https://auth.casmart.internal/if/admin/
2. Clic en tu usuario (arriba derecha)
3. Account → API Tokens
4. Clic en "Create"
5. Nombre: "Login Manager Sync"
6. Copiar token generado
```

**Opción 2: Via API (Para automatización)**
```bash
curl -X POST http://auth.casmart.internal/api/v3/admin/access_tokens/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Login Manager Sync",
    "expiring": false
  }'
```

---

## ✅ Checklist Post-Setup

- [ ] AUTHENTIK_API_TOKEN configurado en .env del backend
- [ ] Endpoint `/api/v1/emails/export/{type}` responde correctamente
- [ ] Endpoint `/api/v1/emails/sync-to-authentik` responde correctamente
- [ ] Script `sync_emails_to_authentik.py` ejecuta sin errores
- [ ] Email de prueba contiene logo, colores y nuevo contenido
- [ ] Documentación de manual guardada en equipo

---

## 📞 Soporte

Si tienes problemas:
1. Verifica que Authentik está accesible: `curl http://auth.casmart.internal/`
2. Verifica el token: `curl -H "Authorization: Bearer $TOKEN" http://auth.casmart.internal/api/v3/core/email_templates/`
3. Revisa logs del backend: `docker logs casmarts-login-backend`
4. Prueba sincronización manual via UI

