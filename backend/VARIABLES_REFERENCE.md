# 📧 Referencia Completa de Variables para Plantillas de Email

## Variables Disponibles por Categoría

### 👤 Datos del Usuario

```html
{{nombre_usuario}}          <!-- Nombre completo: Israel Martínez -->
{{nombre_usuario_nombre}}   <!-- Solo nombre: Israel -->
{{nombre_usuario_apellido}} <!-- Solo apellido: Martínez -->
{{usuario_login}}           <!-- ID de acceso: israelm -->
{{usuario_email}}           <!-- Correo: israelm@casmarts.com -->
```

**Ejemplo de uso:**
```html
<p>Hola <strong>{{nombre_usuario}}</strong>,</p>
<p>Tu usuario: <code>{{usuario_login}}</code></p>
<p>Tu correo registrado: <a href="mailto:{{usuario_email}}">{{usuario_email}}</a></p>
```

---

### 🏢 Datos del Sistema

```html
{{nombre_sistema}}        <!-- Sistema donde ocurre el evento: CASMARTS Core -->
{{empresa_nombre}}        <!-- Nombre de la empresa: C&A Smart Systems -->
{{aplicacion_nombre}}     <!-- Aplicación: Portal RH -->
{{aplicacion_slug}}       <!-- ID único: portal-rh -->
```

**Ejemplo de uso:**
```html
<p>Se ha solicitado un cambio en <strong>{{aplicacion_nombre}}</strong></p>
<p>Sistema: {{nombre_sistema}} | Empresa: {{empresa_nombre}}</p>
```

---

### 🎨 Datos de Marca

```html
{{color_primario}}        <!-- Hex color corporativo: #4272A5 -->
{{logo_url}}             <!-- URL del logo corporativo (header) -->
```

El logo de "Plataforma de Administración" (pie de página) **no es una variable `{{ }}`** — se inyecta
automáticamente en el wrapper (`email_base_unified.html.j2`) a partir del logo inferior configurado
en el tema (ConfigPanel → Logos). No hace falta ni se puede insertar manualmente en el `body_html`.

**Ejemplo de uso (en CSS inline):**
```html
<p style="color: {{color_primario}}; font-weight: bold;">Aviso de Seguridad</p>
```

---

### 🔒 Contexto Técnico y Seguridad

```html
{{ip_origen}}     <!-- IP remota: 192.168.1.100 -->
{{navegador}}     <!-- User-Agent: Mozilla/5.0 Chrome/120.0... -->
{{dispositivo}}   <!-- Dispositivo detectado: Windows, macOS, Linux, iOS, Android -->
```

**Ejemplo de uso:**
```html
<table>
  <tr>
    <td>IP de origen:</td>
    <td><code>{{ip_origen}}</code></td>
  </tr>
  <tr>
    <td>Navegador:</td>
    <td>{{dispositivo}}</td>
  </tr>
  <tr>
    <td>User-Agent:</td>
    <td><small>{{navegador}}</small></td>
  </tr>
</table>
```

---

### 📅 Datos de Evento

```html
{{fecha_evento}}        <!-- Fecha legible: 30/06/2026 14:32 -->
{{fecha_hora_cambio}}   <!-- ISO format: 2026-06-30T14:32:45.123456 -->
{{realizado_por}}       <!-- Quién ejecutó: Usuario: Israel Martínez -->
```

**Ejemplo de uso:**
```html
<p>Cambio realizado: <strong>{{fecha_evento}}</strong></p>
<p>Por: <strong>{{realizado_por}}</strong></p>
```

---

### 🔗 Acceso y Contacto

```html
{{url_acceso}}       <!-- URL del sistema: https://auth.casmart.internal/if/flow/... -->
{{contacto_soporte}} <!-- Email de soporte: soporte@casmarts.internal -->
```

**Ejemplo de uso:**
```html
<a href="{{url_acceso}}" style="background-color: {{color_primario}}; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none;">
  Acceder al Sistema
</a>

<p>Si necesitas ayuda, contacta a <a href="mailto:{{contacto_soporte}}">{{contacto_soporte}}</a></p>
```

---

### 📋 Específicas por Evento

#### Alta de Usuario (new_account)
```html
{{rol_asignado}}     <!-- Rol asignado: Administrador, Operador, etc. -->
```

**Importante:** por mandato de producto, `new_account` **nunca envía una contraseña por correo**
(ni siquiera temporal). El CTA "Establecer contraseña" usa el mismo flow de recuperación que
`password_reset` (`{{url_acceso}}` → enlace de un solo uso, expira en 24h).

Los eventos `account_lockout` (bloqueo temporal de seguridad, no una baja permanente) y
`security_change` (confirmación de que la contraseña ya fue cambiada) usan únicamente las
variables comunes de arriba — no tienen variables propias adicionales.

---

### 🔧 Legales y Configuración

```html
{{footer_legal}}     <!-- Leyenda legal, confidencialidad, etc. -->
{{anio}}            <!-- Año actual para copyright: 2026 -->
```

**Ejemplo de uso:**
```html
<footer style="text-align: center; font-size: 11px; color: #999;">
  <p>© {{anio}} C&A Smart Systems. Todos los derechos reservados.</p>
  <p>{{footer_legal}}</p>
</footer>
```

---

## 📝 Ejemplo Completo

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Bienvenido a {{nombre_sistema}}</title>
</head>
<body>
  <!-- Encabezado -->
  <div style="background-color: {{color_primario}}; padding: 20px; text-align: center;">
    <img src="{{logo_url}}" alt="Logo" style="max-height: 60px;">
    <h1 style="color: white; margin: 10px 0;">{{nombre_sistema}}</h1>
  </div>

  <!-- Contenido principal -->
  <div style="padding: 30px; font-family: Arial, sans-serif;">
    <p>Hola <strong>{{nombre_usuario_nombre}}</strong>,</p>
    
    <p>Tu cuenta en <strong>{{aplicacion_nombre}}</strong> ha sido creada exitosamente.</p>
    
    <!-- Tabla de detalles -->
    <table style="width: 100%; border-collapse: collapse;">
      <tr>
        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Nombre:</strong></td>
        <td style="padding: 10px; border: 1px solid #ddd;">{{nombre_usuario}}</td>
      </tr>
      <tr>
        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Usuario:</strong></td>
        <td style="padding: 10px; border: 1px solid #ddd;">{{usuario_login}}</td>
      </tr>
      <tr>
        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Correo:</strong></td>
        <td style="padding: 10px; border: 1px solid #ddd;">{{usuario_email}}</td>
      </tr>
      <tr>
        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Rol:</strong></td>
        <td style="padding: 10px; border: 1px solid #ddd;">{{rol_asignado}}</td>
      </tr>
      <tr>
        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Fecha de creación:</strong></td>
        <td style="padding: 10px; border: 1px solid #ddd;">{{fecha_evento}}</td>
      </tr>
    </table>

    <!-- Nota de seguridad -->
    <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
      <p><strong>⚠️ Nota de seguridad:</strong></p>
      <p>Si tú no solicitaste esta cuenta, contacta inmediatamente a <strong>{{contacto_soporte}}</strong>.</p>
      <p style="font-size: 11px; color: #666;">
        Esta cuenta fue creada desde IP <code>{{ip_origen}}</code> en {{dispositivo}}.
      </p>
    </div>

    <!-- CTA -->
    <div style="text-align: center; margin: 30px 0;">
      <a href="{{url_acceso}}" 
         style="background-color: {{color_primario}}; color: white; padding: 12px 30px; 
                text-decoration: none; border-radius: 6px; font-weight: bold; 
                display: inline-block;">
        Acceder a {{nombre_sistema}}
      </a>
    </div>

    <!-- Información adicional -->
    <p style="font-size: 12px; color: #666;">
      <strong>Por seguridad:</strong> el enlace de arriba es de un solo uso y expira en 24 horas.
    </p>
  </div>

  <!-- El pie de página (logo de plataforma + aviso automático + soporte + copyright)
       lo agrega automáticamente el wrapper — no se escribe aquí. -->
</body>
</html>
```

---

## 🔄 Flujo de Variables en Authentik

```
Usuario realiza acción en Authentik
        ↓
Authentik dispara evento
        ↓
Backend captura: user, ip, navegador, aplicación
        ↓
Backend sustituye variables en template {{...}}
        ↓
Envía email con datos reales
```

---

## ✅ Checklist para Plantillas

- [ ] ¿Usas {{nombre_usuario}} en lugar de {{usuario_login}}? (Más personal)
- [ ] ¿Incluyes {{ip_origen}} y {{dispositivo}} en sección de seguridad?
- [ ] ¿Tienes un {{contacto_soporte}} clickeable en caso de problema?
- [ ] ¿Están los {{url_acceso}} con estilos apropiados?
- [ ] ¿Utilizas {{color_primario}} para mantener identidad de marca?
- [ ] ¿Tienes nota de seguridad en eventos sensibles (baja, cambio de contraseña)?

