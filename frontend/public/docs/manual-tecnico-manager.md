# Manual Técnico y de Arquitectura - Authentik Login Manager

## 1. Introducción y Propósito
El **Authentik Login Manager** es un centro de control y panel de administración construido con **React (v18+)** y un backend en **FastAPI (Python)**. Su principal función es la de administrar los parámetros de los flujos de correo de Authentik (como la recuperación de contraseña y la verificación de cuentas), permitiendo personalizar de manera visual los asuntos, logos, firmas y contenidos HTML de los correos automáticos.

---

## 2. Arquitectura de Software

```mermaid
graph TD
    A[Cliente: React Frontend] -->|REST API + X-Admin-Key| B[Nginx Gateway]
    B -->|FastAPI API| C[FastAPI Backend]
    C -->|Base de Datos PostgreSQL| D[PostgreSQL 16 DB]
    C -->|API REST Interna| E[Authentik Admin API]
```

### 2.1. Frontend (React)
El frontend está desarrollado con **React** y empaquetado con **Vite**:
* **Tailwind CSS 3.4 & Lucide Icons:** Proporcionan una interfaz limpia, responsiva y de aspecto premium para la administración de las plantillas.
* **Componentes de Formulario Reactivos:** Facilitan la actualización y sincronización de datos de correos en tiempo real mediante estados de React.
* **TipTap Editor:** Editor visual WYSIWYG incorporado para la redacción y maquetación de los cuerpos de correo en formato HTML, con soporte directo para variables del contexto de Authentik.

### 2.2. Backend (FastAPI)
* **FastAPI:** Expone las APIs para la sincronización.
* **PostgreSQL:** Registra las plantillas de correo editadas para cada flujo.
* **Integración API de Authentik:** Cuando se solicita un despliegue, el backend traduce el contenido HTML editado a una plantilla Jinja compatible con Authentik, y la inyecta directamente en el objeto `EmailStage` correspondiente a través de la API administrativa de Authentik.

---

## 3. Flujo de Sincronización Dinámica de Plantillas de Correo
Cuando un administrador hace clic en "Aplicar a Authentik" para un flujo (por ejemplo, `password-recovery`):
1. **Compilación de Plantilla HTML:** El backend toma el cuerpo HTML editado por el usuario y le inyecta la cabecera dinámica, pie de página e imágenes correspondientes (ej. logo de Starter o Centinela) basándose en las variables detectadas de la sesión de origen.
2. **API Call:** Se realiza una llamada HTTP `PUT` o `PATCH` autenticada contra la API de Authentik `/api/v3/stages/email/{uuid}/` enviando el código HTML de la plantilla compilada.
3. **Persistencia Local:** Se guarda el borrador y estado de sincronización en la base de datos PostgreSQL local.

---

## 4. Configuración y Despliegue
El proyecto se controla mediante variables de entorno configuradas en el archivo `.env`:

```ini
# Configuración del Backend
DATABASE_URL=postgresql+asyncpg://manager_user:YourSecurePassword@postgres:5432/authentik_login_manager
ADMIN_API_KEY=admin_api_key_hex_value

# URL de Conexión a Authentik
AUTHENTIK_URL=http://casmarts-core-authentik-server:9000
AUTHENTIK_TOKEN=your_authentik_admin_api_token
```
