# Guía Técnica Avanzada: Integración y Personalización Directa vía API

Esta guía detalla el funcionamiento interno de la API de **Login Manager** y **Login Designer**, describiendo cómo consumir y aplicar los datos de personalización de temas (colores, fuentes, logos, configuraciones de UI y traducciones) y las plantillas de correos electrónicos directamente en aplicaciones cliente o integraciones personalizadas.

---

## 📌 1. Arquitectura de Datos y Flujo Core

Tanto el **Login Manager** como el **Login Designer** comparten y guardan datos en una base de datos centralizada (PostgreSQL). Los datos clave residen en las siguientes tablas:

1. **`tenant_themes`**: Contiene la configuración visual del portal (colores primarios, de fondo, logos en base64, PDFs de privacidad, flags de visibilidad de componentes y configuraciones extendidas de Authentik).
2. **`tenant_email_bodies`**: Contiene las plantillas de correo personalizadas por tenant/flujo/aplicación para los 13 tipos de eventos soportados.

Cualquier cambio realizado en las UIs se expone de forma inmediata a través de la API REST para que portales a medida puedan renderizar la misma identidad visual sin duplicar la lógica.

---

## ⚡ 2. Endpoints Core de la API de Temas

### 🔍 Obtener el Tema Activo
Para que una aplicación externa o portal a medida renderice dinámicamente el branding correcto, debe consultar el endpoint público.

*   **Endpoint**: `GET /api/v1/public/theme/{flow_slug}`
*   **Cabecera de Tenant (Obligatoria)**: `X-Tenant-Domain: <dominio_del_tenant>`
*   **Parámetro opcional**: `?app_slug=<slug_de_la_app>` (para temas específicos por aplicación)

#### Ejemplo de Solicitud:
```bash
curl -X GET \
  -H "X-Tenant-Domain: casmart.internal" \
  "http://loginmanager.casmart.internal:8000/api/v1/public/theme/default-authentication-flow?app_slug=portal-rh"
```

#### Ejemplo de Respuesta (JSON):
```json
{
  "id": "7a3b4e9f-ca52-44df-b4d2-f1d2a3f4b5c6",
  "authentik_flow_slug": "default-authentication-flow",
  "authentik_app_slug": "portal-rh",
  "display_name": "Portal de Recursos Humanos",
  "system_name": "CASMARTS<br>Core",
  "system_subtitle": "Gobierno del Estado de México",
  "layout_position": "left",
  "primary_color": "#4272A5",
  "hover_color": "#2d5580",
  "card_bg_color": "#FFFFFF",
  "panel_bg_color": "#F6F9FD",
  "bg_type": "gradient",
  "bg_gradient_from": "#c8c4bc",
  "bg_gradient_to": "#a09890",
  "bg_image_base64": null,
  "bg_opacity": 1.0,
  "form_opacity": 0.55,
  "logo_top_base64": "data:image/png;base64,iVBORw0KG...",
  "logo_bottom_base64": "data:image/png;base64,iVBORw0KG...",
  "privacy_pdf_url": "data:application/pdf;base64,JVBER...",
  "allow_self_registration": false,
  "require_email_verification": true,
  "show_social_google": true,
  "show_social_microsoft": false,
  "show_social_gov_id": false,
  "show_forgot_password": true,
  "show_logos_panel": true,
  "show_password_toggle": true,
  "show_system_name": true,
  "show_system_subtitle": true,
  "show_field_labels": true,
  "show_app_message": true,
  "email_footer_text": "Este correo es confidencial.",
  "custom_messages": {
    "forgot your username or password?": "¿Olvidaste tus credenciales?",
    "enter your username or email address.": "Ingresa tu usuario institucional"
  },
  "expansion_config": {
    "custom_css": ".my-btn { border-radius: 20px; }",
    "custom_js": "console.log('Casmarts Theme Loaded');"
  }
}
```

---

## 🎨 3. Aplicación Manual de Estilos (Frontend Custom)

Si estás construyendo un portal a medida y deseas replicar con exactitud el diseño establecido en el Designer:

### A. Colores e Identidad (CSS Variables)
Inyecta las propiedades CSS personalizadas dinámicamente en el elemento `:root` o contenedor padre al recibir el JSON de la API:

```javascript
// Al recibir la respuesta del API de temas
function aplicarTema(themeData) {
  const root = document.documentElement;
  
  // Asignar colores core
  root.style.setProperty('--primary-color', themeData.primary_color);
  root.style.setProperty('--primary-hover', themeData.hover_color);
  root.style.setProperty('--card-bg', themeData.card_bg_color);
  root.style.setProperty('--panel-bg', themeData.panel_bg_color);
  
  // Configurar fondo dinámico
  if (themeData.bg_type === 'color') {
    root.style.setProperty('--app-bg', themeData.bg_flat_color || '#ffffff');
  } else if (themeData.bg_type === 'gradient') {
    root.style.setProperty('--app-bg', `linear-gradient(135deg, ${themeData.bg_gradient_from}, ${themeData.bg_gradient_to})`);
  } else if (themeData.bg_type === 'image' && themeData.bg_image_base64) {
    root.style.setProperty('--app-bg', `url(${themeData.bg_image_base64})`);
  }

  // Inyectar CSS y JS extendidos (Expansion Config) si existen
  if (themeData.expansion_config?.custom_css) {
    const styleEl = document.createElement('style');
    styleEl.innerHTML = themeData.expansion_config.custom_css;
    document.head.appendChild(styleEl);
  }
  
  if (themeData.expansion_config?.custom_js) {
    const scriptEl = document.createElement('script');
    scriptEl.innerHTML = themeData.expansion_config.custom_js;
    document.body.appendChild(scriptEl);
  }
}
```

### B. Traducciones y Mensajes Dinámicos
Authentik devuelve textos por defecto en inglés (ej: `"Forgot your username or password?"`). Tu aplicación puede utilizar `custom_messages` como un mapa de traducción directa:

```javascript
function traducirTexto(originalText) {
  const key = originalText.toLowerCase().trim();
  return themeData.custom_messages?.[key] || originalText;
}
```

---

## 📧 4. Gestión Avanzada de Emails vía API

El sistema soporta 13 tipos de eventos que se sincronizan con Authentik para mantener una identidad de correo unificada:

| Clave del Evento (`event_type`) | Significado / Contexto |
| :--- | :--- |
| `password_reset` | Recuperación de contraseña iniciada por el usuario. |
| `new_account` | Correo de bienvenida y activación de nueva cuenta. |
| `account_lockout` | Notificación automática por intentos fallidos de login. |
| `email_verification` | Enlace para validar el correo del usuario. |
| `security_change` | Confirmación de cambio de contraseña o datos de acceso. |
| `account_locked_admin` | Alerta de que un administrador bloqueó la cuenta. |
| `account_unlocked_admin` | Alerta de que la cuenta fue reactivada por un administrador. |
| `login_success` | Alerta de inicio de sesión exitoso (detección de intrusos). |
| `suspicious_request` | Alerta por IP inusual o país no reconocido. |
| `invitation_used` | Confirmación de que se aceptó una invitación de registro. |
| `app_authorized` | Consentimiento OAuth/OIDC otorgado a una nueva aplicación. |
| `impersonation_started` | Alerta crítica de acceso de soporte (suplantación permitida). |
| `account_deleted` | Confirmación irrevocable de eliminación de cuenta. |

### 🛠️ Obtener la Plantilla por Defecto
Útil para restablecer el HTML original de un evento de correo.

*   **Endpoint**: `GET /api/v1/admin/{flow_slug}/emails/default-body/{event_type}`
*   **Cabeceras**: `X-Admin-Key: <llave_secreta>`
*   **Respuesta**:
    ```json
    {
      "subject": "Restablecer contraseña",
      "body_html": "<h1...>Hola {{nombre_usuario}}...</h1...>"
    }
    ```

### 📤 Exportar HTML Renderizado Total
Este endpoint devuelve el HTML definitivo listo para enviarse por SMTP o guardarse en un servicio externo. Realiza el renderizado del template base (`email_base_unified.html.j2`) inyectando el logotipo base64 y los colores definidos en el tema.

*   **Endpoint**: `GET /api/v1/admin/{flow_slug}/emails/preview/{event_type}`
*   **Parámetros query opcionales**:
    *   `user_email`: Correo del usuario de prueba.
    *   `username`: Login / ID del usuario.
*   **Respuesta**: Un documento HTML (`text/html`) completo con estilos CSS integrados/inlined.

---

## ⚡ 5. Sincronización Programática con Authentik (Webhooks & CI/CD)

Si deseas forzar la sincronización de las plantillas desde scripts automáticos o tuberías de CI/CD:

```bash
# Sincronizar un evento específico a Authentik
curl -X POST \
  -H "X-Admin-Key: <tu_admin_key>" \
  -H "X-Tenant-Domain: casmart.internal" \
  "http://loginmanager.casmart.internal:8000/api/v1/emails/sync-to-authentik?event_type=password_reset"
```

Esto recupera la plantilla personalizada de la base de datos de Login Manager, la ensambla con la estructura base y la envía a la API de Authentik utilizando el token configurado en `AUTHENTIK_API_TOKEN`.

---

## 🛡️ 6. Consideraciones de Seguridad Avanzadas

1.  **Prevención de SMTP Header Injection (CWE-93)**:
    Si utilizas la API para enviar correos directamente desde tu backend, asegúrate de procesar las variables del asunto (`subject`) y el destinatario (`to_email`) con una limpieza estricta de caracteres de control (`\r`, `\n`) antes de pasarlos al servidor de correo.
2.  **Tamaño de Recursos Base64**:
    Las imágenes y PDFs se guardan en la base de datos codificados en Base64. Para evitar sobrecargar la carga útil de los correos electrónicos o de las solicitudes HTTP, el backend omite automáticamente logos en correos si superan los **200 KB**. Te recomendamos optimizar todas las imágenes antes de guardarlas vía API.
3.  **Seguridad de CORS**:
    Los endpoints públicos (`/api/v1/public/*`) permiten llamadas directas desde navegadores para que la UI pueda resolverse en tiempo de render. Los endpoints administrativos (`/api/v1/admin/*`) están protegidos estrictamente por la cabecera `X-Admin-Key`.
