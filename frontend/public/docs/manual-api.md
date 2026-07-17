# Manual de Uso de la API - Authentik Login Designer & Manager

Este documento detalla los endpoints de la API expuestos por los backends de los proyectos **Authentik Login Designer** y **Authentik Login Manager** para la administración de temas de interfaz y plantillas de correo.

---

## 1. Autenticación
Todos los endpoints de administración (creación, edición, borrado y despliegue) requieren la cabecera HTTP `X-Admin-Key` con la clave de API configurada en las variables de entorno (`ADMIN_API_KEY`).

Ejemplo de cabecera:
```http
X-Admin-Key: 30043c1626354b3da5cb22d0577a7ef9
```

---

## 2. Endpoints de la API del Designer (Temas de Interfaz)

### 2.1. Listar Temas Registrados
* **Ruta:** `GET /api/v1/themes`
* **Cabeceras obligatorias:** `X-Admin-Key`
* **Respuesta exitosa (200 OK):**
```json
[
  {
    "authentik_flow_slug": "default-authentication-flow",
    "authentik_app_slug": "starter",
    "display_name": "Starter CASMartS",
    "primary_color": "#1c3d5a",
    "hover_color": "#2c5282"
  }
]
```

### 2.2. Obtener Detalles de un Tema por Flow
* **Ruta:** `GET /api/v1/themes/{flow_slug}`
* **Respuesta exitosa (200 OK):**
```json
{
  "authentik_flow_slug": "default-authentication-flow",
  "authentik_app_slug": "starter",
  "display_name": "Starter CASMartS",
  "system_name": "CASMartS Core",
  "system_subtitle": "Starter",
  "primary_color": "#1c3d5a",
  "hover_color": "#2c5282",
  "layout_position": "left",
  "bg_type": "gradient",
  "bg_gradient_from": "#1a365d",
  "bg_gradient_to": "#2a4365",
  "logo_top_text": "CASMartS Systems"
}
```

### 2.3. Guardar o Actualizar un Tema (Upsert)
* **Ruta:** `POST /api/v1/themes`
* **Cabeceras obligatorias:** `X-Admin-Key`
* **Cuerpo de la petición (JSON):**
```json
{
  "authentik_flow_slug": "default-authentication-flow",
  "authentik_app_slug": "starter",
  "display_name": "Starter Portal",
  "system_name": "CASMartS",
  "system_subtitle": "Starter App",
  "primary_color": "#0F4C81",
  "hover_color": "#1A568D",
  "layout_position": "left",
  "bg_type": "color",
  "bg_flat_color": "#F0F4F8"
}
```
* **Respuesta (200 OK / 201 Created):** Retorna el objeto JSON del tema guardado.

### 2.4. Desplegar un Tema a Authentik
Compila los estilos personalizados, inyecta el CSS dinámico en la plantilla base y realiza el despliegue directo sobre el servidor de Authentik.
* **Ruta:** `POST /api/v1/themes/{flow_slug}/deploy`
* **Cabeceras obligatorias:** `X-Admin-Key`
* **Respuesta exitosa (200 OK):**
```json
{
  "status": "success",
  "message": "Theme successfully compiled and deployed to Authentik server."
}
```

---

## 3. Endpoints de la API del Manager (Plantillas de Correo)

### 3.1. Obtener la Configuración de Correo para un Flow
* **Ruta:** `GET /api/v1/emails/{flow_slug}`
* **Cabeceras obligatorias:** `X-Admin-Key`
* **Respuesta exitosa (200 OK):**
```json
{
  "flow_slug": "password-recovery",
  "logo_url": "https://auth.casmart.internal/static/dist/assets/images/starter_logo.png",
  "email_subject": "Recuperación de contraseña",
  "email_body_html": "<p>Hola {{ user.username }}, haz clic en el enlace para restablecer tu contraseña.</p>"
}
```

### 3.2. Sincronizar y Desplegar Plantilla de Correo a Authentik
Actualiza la configuración en la base de datos local y sincroniza la plantilla HTML de correo generada dinámicamente con la configuración del stage de correo correspondiente en Authentik.
* **Ruta:** `POST /api/v1/emails/{flow_slug}/deploy-to-authentik`
* **Cabeceras obligatorias:** `X-Admin-Key`
* **Cuerpo de la petición (JSON):**
```json
{
  "email_subject": "Recuperar Acceso",
  "email_body_html": "<p>Haz clic en: <a href='{{ url }}'>Enlace</a></p>"
}
```
* **Respuesta exitosa (200 OK):**
```json
{
  "status": "success",
  "message": "Email template deployed to Authentik successfully."
}
```
