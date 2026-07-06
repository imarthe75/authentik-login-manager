import json
import base64
import re
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy import text
from app.database import get_db
from app.models.tenant_theme import TenantTheme
from app.schemas.theme import ThemePublic
from app.cache import cache
from app.config import settings

logger = logging.getLogger("authentik_login_manager.public")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/v1/public", tags=["Public Themes"])

authentik_engine = create_async_engine(
    settings.DATABASE_URL.replace("authentik_login_manager", "authentik"),
    echo=False,
    pool_pre_ping=True
)

# Generic default fallback theme config
DEFAULT_THEME = {
    "display_name": "CASMARTS",
    "system_name": "CASMARTS<br>Core",
    "system_subtitle": "Gobierno del estado de México",
    "layout_position": "left",
    "name_align": "center",
    "subtitle_align": "center",
    "privacy_align": "center",
    "primary_color": "#4272A5",
    "hover_color": "#2d5580",
    "card_bg_color": "#FFFFFF",
    "panel_bg_color": "#F6F9FD",
    "bg_type": "gradient",
    "bg_flat_color": None,
    "bg_gradient_from": "#c8c4bc",
    "bg_gradient_to": "#a09890",
    "bg_opacity": 1.0,
    "form_opacity": 0.55,
    "form_height_pct": None,
    "logos_opacity": 0.55,
    "logos_height_pct": None,
    "privacy_pdf_url": "/static/aviso_privacidad.pdf",
    "authentik_app_slug": None,
    "has_logo_top": False,
    "has_logo_bottom": False,
    "has_bg_image": False,
    "logo_top_text": None,
    "logo_bottom_text": None,
    "custom_messages": {},
    "expansion_config": {}
}

async def resolve_app_slug(app: Optional[str]) -> Optional[str]:
    if not app:
        return None
    try:
        async with authentik_engine.connect() as conn:
            query = text("""
                SELECT app.slug 
                FROM authentik_core_application app
                JOIN authentik_providers_oauth2_oauth2provider prov ON app.provider_id = prov.provider_ptr_id
                WHERE prov.client_id = :client_id
                LIMIT 1;
            """)
            res = await conn.execute(query, {"client_id": app})
            row = res.fetchone()
            if row:
                logger.info(f"Resolved app client_id='{app}' to app_slug='{row[0]}'")
                return row[0]
    except Exception as e:
        logger.error(f"Error resolving client_id to app slug: {e}")
    return app

@router.get("/theme/{flow_slug}", response_model=ThemePublic)
async def get_public_theme(
    flow_slug: str,
    app: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    if app:
        app = await resolve_app_slug(app)
        
    cache_key = f"theme:{flow_slug}:{app or 'global'}"
    logger.info(f"Retrieving public theme for flow_slug='{flow_slug}', app='{app or 'global'}'")
    
    # 1. Try to fetch from Valkey Cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        try:
            logger.info(f"Cache hit for key '{cache_key}'")
            return ThemePublic(**json.loads(cached_data))
        except Exception as e:
            logger.error(f"Failed to parse cached data for key '{cache_key}': {e}")
            pass

    logger.info(f"Cache miss for key '{cache_key}'. Fetching from database...")

    # 2. Check Database - Prioritize application-specific theme if app is provided
    db_theme = None
    if app:
        logger.info(f"Querying DB for application-specific theme with authentik_app_slug='{app}' and flow_slug='{flow_slug}'")
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug == app
        )
        result = await db.execute(stmt)
        db_theme = result.scalar_one_or_none()
        if db_theme:
            logger.info(f"Found database theme specifically for app='{app}' with flow='{flow_slug}' (ID: {db_theme.id})")

    if not db_theme:
        # Fallback: global theme for this flow (app_slug IS NULL — not app-specific)
        logger.info(f"Querying DB for global flow theme with authentik_flow_slug='{flow_slug}' and no app_slug")
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        )
        result = await db.execute(stmt)
        db_theme = result.scalar_one_or_none()
        if db_theme:
            logger.info(f"Found global flow theme for flow_slug='{flow_slug}' (ID: {db_theme.id})")

    # Fallback to default-authentication-flow global theme if no theme exists for this flow
    if not db_theme and flow_slug != "default-authentication-flow":
        logger.info(f"Querying DB for fallback global theme 'default-authentication-flow' because no theme was found for '{flow_slug}'")
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == "default-authentication-flow",
            TenantTheme.authentik_app_slug.is_(None)
        )
        result = await db.execute(stmt)
        db_theme = result.scalar_one_or_none()

    if db_theme:
        theme_dict = {
            "display_name": db_theme.display_name,
            "system_name": db_theme.system_name,
            "system_subtitle": db_theme.system_subtitle,
            "layout_position": db_theme.layout_position,
            "name_align": db_theme.name_align,
            "subtitle_align": db_theme.subtitle_align,
            "privacy_align": db_theme.privacy_align,
            "primary_color": db_theme.primary_color,
            "hover_color": db_theme.hover_color,
            "card_bg_color": db_theme.card_bg_color,
            "panel_bg_color": db_theme.panel_bg_color,
            "bg_type": db_theme.bg_type,
            "bg_flat_color": db_theme.bg_flat_color,
            "bg_gradient_from": db_theme.bg_gradient_from,
            "bg_gradient_to": db_theme.bg_gradient_to,
            "bg_opacity": db_theme.bg_opacity,
            "form_opacity": db_theme.form_opacity,
            "form_height_pct": db_theme.form_height_pct,
            "logos_opacity": db_theme.logos_opacity,
            "logos_height_pct": db_theme.logos_height_pct,
            "privacy_pdf_url": db_theme.privacy_pdf_url,
            "authentik_app_slug": db_theme.authentik_app_slug,
            "has_logo_top": bool(db_theme.logo_top_base64),
            "has_logo_bottom": bool(db_theme.logo_bottom_base64),
            "has_bg_image": bool(db_theme.bg_image_base64),
            "logo_top_text": db_theme.logo_top_text or None,
            "logo_bottom_text": db_theme.logo_bottom_text or None,
            "allow_self_registration": db_theme.allow_self_registration,
            "show_social_google": db_theme.show_social_google,
            "show_social_microsoft": db_theme.show_social_microsoft,
            "show_social_gov_id": db_theme.show_social_gov_id,
            "show_forgot_password": db_theme.show_forgot_password,
            "show_logos_panel": db_theme.show_logos_panel,
            "show_password_toggle": db_theme.show_password_toggle,
            "show_system_name": db_theme.show_system_name,
            "show_system_subtitle": db_theme.show_system_subtitle,
            "show_field_labels": db_theme.show_field_labels,
            "is_custom": True,  # theme exists in DB
            "custom_messages": db_theme.custom_messages or {},
            "expansion_config": db_theme.expansion_config or {},
        }
    else:
        logger.warning(f"No custom theme found for app='{app}' or flow_slug='{flow_slug}'. Using default theme.")
        # Prevent Authentik from breaking: return fallback default theme config
        theme_dict = DEFAULT_THEME.copy()
        theme_dict["display_name"] = flow_slug.replace("-", " ").title()
        theme_dict["is_custom"] = False  # no theme designed — use Authentik native

    # Save compiled public representation to Valkey (TTL 5 minutes = 300 seconds)
    logger.info(f"Caching retrieved theme for key '{cache_key}' with 300s TTL")
    await cache.set(cache_key, json.dumps(theme_dict), ex=300)
    
    return ThemePublic(**theme_dict)

@router.get("/theme/{flow_slug}/image/{field}")
async def get_theme_image(
    flow_slug: str,
    field: str,
    app: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    if app:
        app = await resolve_app_slug(app)
        
    logger.info(f"Retrieving theme image for flow_slug='{flow_slug}', field='{field}', app='{app or 'global'}'")
    if field not in ["logo_top", "logo_bottom", "bg_image"]:
        logger.error(f"Invalid image field requested: '{field}'")
        raise HTTPException(status_code=400, detail="Invalid image field requested.")

    db_theme = None
    if app:
        logger.info(f"Querying DB for theme image with authentik_app_slug='{app}' and flow_slug='{flow_slug}'")
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug == app
        )
        result = await db.execute(stmt)
        db_theme = result.scalar_one_or_none()

    if not db_theme:
        logger.info(f"Querying DB for global theme image with authentik_flow_slug='{flow_slug}' and no app_slug")
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        )
        result = await db.execute(stmt)
        db_theme = result.scalar_one_or_none()

    if not db_theme and flow_slug != "default-authentication-flow":
        logger.info(f"Querying DB for fallback global theme image from 'default-authentication-flow' because no theme was found for '{flow_slug}'")
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == "default-authentication-flow",
            TenantTheme.authentik_app_slug.is_(None)
        )
        result = await db.execute(stmt)
        db_theme = result.scalar_one_or_none()

    if not db_theme:
        logger.warning(f"No custom theme found for flow_slug='{flow_slug}' or app='{app}' (even with fallback). Cannot serve image.")
        raise HTTPException(status_code=404, detail="Theme or flow slug not found.")

    base64_str = getattr(db_theme, f"{field}_base64", None)
    if not base64_str:
        logger.warning(f"Image for field '{field}' is not set in database for theme ID {db_theme.id}")
        raise HTTPException(status_code=404, detail=f"Image for field '{field}' is not set.")

    # Solo rasters seguros — se excluye deliberadamente image/svg+xml, que puede
    # contener <script> embebido y habilitar XSS al servirse inline.
    ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/x-icon"}

    try:
        pattern = r"^data:(image/[a-zA-Z0-9\+\-\.]+);base64,(.+)$"
        match = re.match(pattern, base64_str.strip())
        if not match:
            # No adivinar el tipo de datos no reconocidos: podría no ser una imagen.
            logger.error(f"Malformed base64 data URI for field '{field}' on theme {db_theme.id}")
            raise HTTPException(status_code=422, detail="Stored image data is not a valid data URI.")

        content_type = match.group(1).lower()
        if content_type not in ALLOWED_IMAGE_TYPES:
            logger.error(f"Rejected disallowed image MIME type '{content_type}' for field '{field}'")
            raise HTTPException(status_code=422, detail=f"Unsupported image type: {content_type}")

        raw_b64 = match.group(2)
        image_data = base64.b64decode(raw_b64, validate=True)
        logger.info(f"Successfully decoded and serving {field} image ({len(image_data)} bytes, {content_type})")
        return Response(content=image_data, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error decoding image for field '{field}': {e}")
        raise HTTPException(status_code=422, detail="Error decoding stored image data.")

@router.post("/theme/invalidate-cache/{flow_slug}", status_code=status.HTTP_200_OK)
async def invalidate_cache(flow_slug: str):
    logger.info(f"Invalidating cache for flow_slug='{flow_slug}'")

    # Delete global and direct keys
    await cache.delete(f"theme:{flow_slug}:global")
    await cache.delete(f"theme:{flow_slug}")

    # Delete all application-specific keys matching the pattern using the underlying Valkey client
    if cache.redis:
        try:
            pattern = f"theme:{flow_slug}:*"
            keys = await cache.redis.keys(pattern)
            if keys:
                await cache.redis.delete(*keys)
                logger.info(f"Successfully invalidated {len(keys)} cached keys matching '{pattern}' in Valkey")
        except Exception as e:
            logger.error(f"Error invalidating cache pattern for '{flow_slug}': {e}")

    return {"status": "success", "message": f"Cache for flow '{flow_slug}' invalidated successfully."}


@router.get("/email-templates")
async def get_email_templates_public():
    """
    Catálogo público de variables `{{ }}` insertables en el editor de correo.
    Debe reflejar exactamente las claves sustituidas en preview_email()/
    send_test_email() (admin.py) para cada uno de los 5 `.j2` reales en
    backend/app/templates/email/ — si agregas una variable nueva a esos
    `preview_subs`/`substitutions`, agrégala aquí también o quedará fuera
    del catálogo que ve el usuario en el editor.
    """
    from app.models.email_body import EMAIL_EVENT_TYPES

    variables_data = [
        # --- DATOS DEL USUARIO ---
        {"variable": "{{nombre_usuario}}", "description": "Nombre completo del usuario (Israel Martínez)"},
        {"variable": "{{nombre_usuario_nombre}}", "description": "Solo nombre del usuario (Israel)"},
        {"variable": "{{nombre_usuario_apellido}}", "description": "Solo apellido del usuario (Martínez)"},
        {"variable": "{{usuario_login}}", "description": "Usuario/ID de acceso (israelm)"},
        {"variable": "{{usuario_email}}", "description": "Correo electrónico del usuario"},

        # --- DATOS DEL SISTEMA ---
        {"variable": "{{nombre_sistema}}", "description": "Nombre del sistema donde ocurre el evento"},
        {"variable": "{{empresa_nombre}}", "description": "Nombre de la empresa (tenant)"},
        {"variable": "{{aplicacion_nombre}}", "description": "Nombre de la aplicación (Portal RH, CRM, etc.)"},
        {"variable": "{{aplicacion_slug}}", "description": "Identificador único de la aplicación"},

        # --- DATOS DE MARCA ---
        {"variable": "{{color_primario}}", "description": "Color primario de la marca (hex)"},
        {"variable": "{{logo_url}}", "description": "URL del logo corporativo"},

        # --- DATOS DEL EVENTO ---
        {"variable": "{{fecha_evento}}", "description": "Fecha y hora del evento (30/06/2026 14:32)"},
        {"variable": "{{fecha_hora_cambio}}", "description": "Fecha/hora exacta del cambio (timestamp)"},
        {"variable": "{{realizado_por}}", "description": "Quién ejecutó la acción (usuario o sistema automático)"},

        # --- CONTEXTO DE RED/SEGURIDAD ---
        {"variable": "{{ip_origen}}", "description": "IP remota desde donde se realizó la acción (192.168.1.100)"},
        {"variable": "{{navegador}}", "description": "Navegador/User-Agent (Mozilla/5.0...)"},
        {"variable": "{{dispositivo}}", "description": "Dispositivo detectado (Chrome en Windows, etc.)"},

        # --- DATOS DE ACCESO ---
        {"variable": "{{url_acceso}}", "description": "Enlace de acceso al sistema"},
        {"variable": "{{contacto_soporte}}", "description": "Correo/teléfono de soporte"},

        # --- LEGALES Y CONFIGURACIÓN ---
        {"variable": "{{footer_legal}}", "description": "Leyenda legal/confidencialidad"},
        {"variable": "{{anio}}", "description": "Año para copyright"},

        # --- ESPECÍFICAS POR EVENTO ---
        {"variable": "{{rol_asignado}}", "description": "[Alta] Rol/perfil asignado"},
    ]

    return {
        "variables": variables_data,
        "event_types": list(EMAIL_EVENT_TYPES),
    }
