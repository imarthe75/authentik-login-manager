# Authentik Login Manager (SaaS Internal CASMARTS)

An internal visual branding panel and dynamic rendering engine to customize, store, and apply distinct visual styles to multiple **Authentik Flows** in real-time. 

With this utility, administrators can design different layouts, configure color palettes, assign custom logos, and define flat, gradient, or image backgrounds without redeploying containers or editing production code.

---

## 🚀 Requisitos y Arranque Rápido

### 1. Variables de Entorno
Crea un archivo `.env` en la raíz de `authentik-login-manager/` (basado en `.env.example`):

```bash
cp .env.example .env
```

### 2. Primer Arranque con Docker Compose
Dado que este proyecto está diseñado para ejecutarse dentro del ecosistema **CASMARTS**, se conecta a la red externa existente `casmarts_network`.

Levanta los contenedores en segundo plano:
```bash
docker compose up -d --build
```

### 3. Ejecutar Migraciones Alembic
Una vez que el servicio de base de datos PostgreSQL esté listo y saludable, ejecuta las migraciones iniciales para crear la tabla de temas visuales y sembrar el flujo predeterminado:
```bash
docker compose exec backend alembic upgrade head
```

---

## 🎨 Integración Paso a Paso en Authentik

Para que Authentik cargue dinámicamente el tema configurado para un flujo específico, sigue estos sencillos pasos:

### Paso 1: Configurar la Plantilla Base en Authentik
1. Sube el archivo de plantilla `login.html.j2` (ubicado en `backend/app/templates/login.html.j2`) al directorio de temas personalizados de tu instancia de Authentik (normalmente montado en `/templates/custom/login.html`).
2. Configura tu flujo (Flow) de inicio de sesión en Authentik para que utilice esta plantilla.

### Paso 2: Crear el Tema Visual en el SaaS
1. Ingresa al panel de administración en `http://localhost:3000`.
2. Presiona el botón **"Agregar Nuevo Portal"** (ícono `+`).
3. Ingresa un **Nombre Amigable** (ej: `CompraMex Portal`) y el **Slug exacto de tu flujo en Authentik** (ej: `default-authentication-flow` o `custom-compramex-flow`).
4. Modifica los colores del botón, opacidades de tarjetas, carga el PDF de Aviso de Privacidad o imágenes personalizadas de logotipo y fondo.
5. Haz clic en **"💾 Guardar y Aplicar"** para guardar en PostgreSQL e invalidar la caché de Valkey.

---

## 🔗 Cómo conectar el volumen compartido con Authentik

El endpoint `POST /api/v1/themes/{flow_slug}/deploy` genera un `login.html` estático con todos los valores del tema ya renderizados y lo escribe en el volumen Docker `authentik-custom-templates` (montado en el backend como `/shared/authentik/templates`).

Para que Authentik lea ese archivo, el volumen debe estar montado también en el contenedor de Authentik bajo la ruta `/templates`.

### Opción A — Authentik en el mismo compose.yml (recomendada)

Si tu instancia de Authentik corre en este mismo `compose.yml`, agrega el volumen a su servicio:

```yaml
services:
  authentik-server:
    # ... tu config existente ...
    volumes:
      - authentik-custom-templates:/templates

  authentik-worker:
    # ... tu config existente ...
    volumes:
      - authentik-custom-templates:/templates
```

### Opción B — Authentik en un compose externo

Si Authentik corre en un `compose.yml` separado (caso habitual en el ecosistema CASMARTS), debes hacer que ambos compartan el mismo volumen con nombre. En el compose de Authentik, declara el volumen como externo:

```yaml
# En el compose.yml de Authentik (ej: ecosistema-casmarts/authentik/compose.yml)
services:
  authentik-server:
    volumes:
      - authentik-login-manager_authentik-custom-templates:/templates

  authentik-worker:
    volumes:
      - authentik-login-manager_authentik-custom-templates:/templates

volumes:
  authentik-login-manager_authentik-custom-templates:
    external: true
```

> **Nota:** El prefijo `authentik-login-manager_` es el nombre del proyecto Docker Compose.
> Cámbialo según el directorio raíz donde ejecutas `docker compose up` en este proyecto.
> Puedes verificar el nombre exacto con: `docker volume ls | grep authentik-custom`

### Configurar la plantilla en Authentik

1. En la interfaz de administración de Authentik → **Flows** → selecciona el flujo de login.
2. En **Stage Bindings** → abre el Stage de tipo `Identification` o `Password`.
3. En la configuración del Stage, establece la **Template** como `login.html`.
4. Guarda y prueba el flujo. La primera vez que ejecutes "Guardar y Aplicar" en el panel, el archivo `login.html` se generará automáticamente en el volumen.

### Variable de entorno requerida

Asegúrate de que `PUBLIC_API_BASE_URL` esté configurada en tu `.env` con la URL pública del backend (accesible desde el navegador del usuario final), ya que esta URL se embebe en el HTML para servir las imágenes de logos y fondo:

```bash
PUBLIC_API_BASE_URL=https://login-manager.casmarts.internal
```

---

## 🗺️ Funcionamiento del Motor Estático (Deploy API)

Cuando el administrador pulsa **"Guardar y Aplicar"**:
1. El tema se guarda en **PostgreSQL 16**.
2. El backend renderiza `login.html.j2` con **Jinja2** usando los valores del tema directamente — sin dependencia de fetch en el cliente.
3. El HTML resultante se escribe en `/shared/authentik/templates/login.html` (volumen compartido con Authentik).
4. La caché de **Valkey** se invalida para ese flow_slug.
5. Authentik sirve el `login.html` estático ya con todos los estilos, textos e imágenes configurados. No se requiere ninguna llamada al API desde la página de login.
