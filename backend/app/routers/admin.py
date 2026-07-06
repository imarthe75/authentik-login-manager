import logging
import re
import secrets
import ssl
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import List, Optional, Dict
import uuid
import httpx
from pathlib import Path
from types import SimpleNamespace
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from app.database import get_db
from app.config import settings
from app.models.tenant import Tenant
from app.models.tenant_theme import TenantTheme
from app.models.email_body import TenantEmailBody, EMAIL_EVENT_TYPES
from app.utils.tenant import extract_tenant_id_from_domain
from app.utils.session import verify_session_token
from app.schemas.theme import (
    ThemeCreate, ThemeUpdate, ThemeUpdateWithEmail,
    ThemeResponse, ThemeResponseWithEmail, EmailBodySchema
)
from app.cache import cache

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/themes", tags=["Admin Themes"])

authentik_engine = create_async_engine(
    settings.DATABASE_URL.replace("authentik_login_manager", "authentik"),
    echo=False,
    pool_pre_ping=True
)


ADMIN_KEY_RATE_LIMIT = 20       # intentos permitidos
ADMIN_KEY_RATE_WINDOW = 300     # por ventana de 5 minutos, por IP


def _admin_rate_limit_client_ip(request: Request) -> str:
    # Todo el tráfico pasa por casmarts-core-gateway, así que
    # request.client.host es SIEMPRE la IP interna del gateway (no la del
    # navegador real) — el rate limit terminaba compartiendo un solo balde
    # entre TODOS los usuarios del panel admin. El gateway sí reenvía
    # X-Real-IP con la IP real (ver subdomains.conf); solo se confía en ese
    # header si la conexión inmediata viene del gateway (mismo check que
    # _is_trusted_proxy_peer usa para X-Tenant-Domain).
    client_ip = request.client.host if request.client else "unknown"
    if _is_trusted_proxy_peer(request):
        client_ip = request.headers.get("X-Real-IP", client_ip)
    return client_ip


async def _register_failed_admin_key_attempt(client_ip: str) -> None:
    # Solo los INTENTOS FALLIDOS cuentan para el límite — este check existe
    # para frenar fuerza bruta contra ADMIN_API_KEY, no para limitar el uso
    # normal de un admin ya autenticado. Antes se incrementaba en cada
    # request (éxito o no): con StrictMode de React duplicando cada fetch en
    # dev y el editor de correos disparando 2 requests por cada cambio de
    # pestaña de evento, un solo admin agotaba el cupo de 20/5min con uso
    # legítimo normal (visto en vivo 2026-07-03).
    rate_key = f"ratelimit:admin_key:{client_ip}"
    attempts = await cache.incr_with_ttl(rate_key, ADMIN_KEY_RATE_WINDOW)
    if attempts is not None and attempts > ADMIN_KEY_RATE_LIMIT:
        log.warning("Rate limit exceeded for X-Admin-Key from IP %s (%s attempts fallidos)", client_ip, attempts)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Try again later."
        )


async def verify_admin_key(
    request: Request,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    admin_session: Optional[str] = Cookie(None),
):
    # Modelo actual (2026-07-06): el navegador nunca conoce ADMIN_API_KEY.
    # /api/v1/auth/login la valida una vez y emite una cookie de sesión
    # HttpOnly firmada (ver app/utils/session.py); el frontend deja de
    # embeber la clave en el bundle (VITE_ADMIN_KEY, hoy eliminado) — antes
    # cualquier visitante podía leerla desde el JS servido al cliente y
    # llamar directamente estos endpoints sin pasar por la UI.
    # X-Admin-Key sigue soportado para automatización server-to-server
    # (scripts, curl) que nunca corre en un navegador.
    if admin_session and verify_session_token(admin_session, settings.SESSION_SECRET):
        return

    client_ip = _admin_rate_limit_client_ip(request)

    if x_admin_key is not None:
        # Comparación constant-time: evita filtrar la clave por diferencias de tiempo.
        if secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
            return  # clave correcta: no consume el cupo de fuerza bruta
        await _register_failed_admin_key_attempt(client_ip)
        log.warning("Invalid X-Admin-Key attempt from IP %s", client_ip)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid administrative credentials."
    )


# ── helpers ─────────────────────────────────────────────────────────────────

async def _load_email_bodies(flow_slug: str, tenant_id: str, db: AsyncSession) -> Dict[str, EmailBodySchema]:
    result = await db.execute(
        select(TenantEmailBody).where(
            TenantEmailBody.tenant_id == tenant_id,
            TenantEmailBody.flow_slug == flow_slug
        )
    )
    return {
        eb.event_type: EmailBodySchema(subject=eb.subject, body_html=eb.body_html)
        for eb in result.scalars().all()
    }


async def _upsert_email_bodies(
    flow_slug: str,
    tenant_id: str,
    bodies: Dict[str, EmailBodySchema],
    db: AsyncSession
) -> None:
    for event_type, body in bodies.items():
        if event_type not in EMAIL_EVENT_TYPES:
            continue
        result = await db.execute(
            select(TenantEmailBody).where(
                TenantEmailBody.tenant_id == tenant_id,
                TenantEmailBody.flow_slug == flow_slug,
                TenantEmailBody.event_type == event_type
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.subject = body.subject
            existing.body_html = body.body_html
            db.add(existing)
        else:
            db.add(TenantEmailBody(
                tenant_id=tenant_id,
                flow_slug=flow_slug,
                event_type=event_type,
                subject=body.subject,
                body_html=body.body_html
            ))


def _build_theme_response_with_email(
    db_theme: TenantTheme, email_bodies: Dict[str, EmailBodySchema]
) -> ThemeResponseWithEmail:
    data = {c.name: getattr(db_theme, c.name) for c in db_theme.__table__.columns}
    return ThemeResponseWithEmail(**data, email_bodies=email_bodies)


async def _update_authentik_scope_descriptions(expansion_config: Optional[dict]) -> None:
    """
    Actualiza las descripciones de scopes personalizadas en la base de datos de Authentik
    si se proporciona una configuración de consentimiento en la expansión.
    """
    if not expansion_config or not isinstance(expansion_config, dict):
        return
    custom_scope_desc = expansion_config.get("consentStage", {}).get("customScopeDescriptions")
    if not custom_scope_desc or not isinstance(custom_scope_desc, dict):
        return
    try:
        async with authentik_engine.begin() as conn:
            for scope, desc in custom_scope_desc.items():
                if scope and desc:
                    await conn.execute(
                        text("UPDATE authentik_providers_oauth2_scopemapping SET description = :desc WHERE scope_name = :scope"),
                        {"desc": str(desc), "scope": str(scope)}
                    )
    except Exception as e:
        log.error(f"Error updating Authentik scope descriptions: {e}")



def _is_trusted_proxy_peer(request: Request) -> bool:
    """
    Defensa en profundidad: aunque el gateway nginx ya sobrescribe
    X-Tenant-Domain/X-Forwarded-Host con el host validado (ver
    core-casmarts/gateway/sites-enabled/subdomains.conf), este backend
    también es alcanzable directamente por cualquier contenedor que
    comparta la red Docker `identity-network` (no hay aislamiento de red
    entre servicios). Sin esta verificación, un contenedor comprometido
    en esa red podría saltarse el gateway y spoofear el tenant directamente.

    Solo se confía en los headers de tenant si la conexión TCP inmediata
    proviene del propio contenedor gateway (resuelto por DNS de Docker en
    cada request, ya que su IP puede cambiar entre reinicios). Si el
    hostname configurado no resuelve (ej. entorno de desarrollo local sin
    gateway), se falla abierto para no romper flujos de dev — el control
    primario sigue siendo el gateway.
    """
    if not request.client:
        return False
    trusted_host = getattr(settings, "TRUSTED_PROXY_HOST", None) or "casmarts-core-gateway"
    try:
        import socket
        trusted_ip = socket.gethostbyname(trusted_host)
    except socket.gaierror:
        log.warning(
            "No se pudo resolver TRUSTED_PROXY_HOST='%s' — confiando en headers de "
            "tenant sin verificar origen (posible entorno de desarrollo).",
            trusted_host,
        )
        return True
    return request.client.host == trusted_ip


async def _get_tenant_context(
    request: Request,
    db: AsyncSession,
    tenant_id: Optional[str] = None
) -> tuple[Tenant, str]:
    """
    Extrae tenant del parámetro tenant_id o del header X-Tenant-Domain / X-Forwarded-Host.
    """
    if tenant_id:
        try:
            val = uuid.UUID(tenant_id)
            result = await db.execute(select(Tenant).where(Tenant.id == val))
            tenant = result.scalar_one_or_none()
            if tenant:
                return tenant, str(tenant.id)
        except ValueError:
            pass

    trusted = _is_trusted_proxy_peer(request)
    if not trusted:
        log.warning(
            "Solicitud con headers de tenant desde origen no confiable (IP=%s) — "
            "ignorando X-Tenant-Domain/X-Forwarded-Host.",
            request.client.host if request.client else "unknown",
        )

    hostname = (
        (trusted and (request.headers.get("X-Tenant-Domain") or request.headers.get("X-Forwarded-Host")))
        or (request.client.host if request.client else "localhost")
    )

    t_id = await extract_tenant_id_from_domain(hostname, db)
    result = await db.execute(
        select(Tenant).where(Tenant.id == t_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant not found or inactive for domain '{hostname}'"
        )

    return tenant, str(tenant.id)


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get("/authentik/applications", dependencies=[Depends(verify_admin_key)])
async def list_authentik_applications(
    request: Request,
    tenant_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        if tenant_id:
            r = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = r.scalar_one_or_none()
        else:
            tenant, _ = await _get_tenant_context(request, db)
            
        async with authentik_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT slug, name FROM authentik_core_application ORDER BY name;")
            )
            apps = [{"slug": row[0], "name": row[1]} for row in result.fetchall()]
            
        if not tenant:
            return apps
            
        domain = (tenant.domain_pattern or "").lower()
        name = (tenant.name or "").lower()
        
        if "usana" in domain or "usana" in name:
            return [app for app in apps if "usana" in app["slug"].lower() or "usana" in app["name"].lower()]
        else:
            return [app for app in apps if "usana" not in app["slug"].lower() and "usana" not in app["name"].lower()]
    except Exception as e:
        log.error(f"Error listing filtered apps: {e}")
        return []


@router.get("", response_model=List[ThemeResponse], dependencies=[Depends(verify_admin_key)])
async def list_themes(
    request: Request,
    tenant_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    tenant, tenant_id = await _get_tenant_context(request, db, tenant_id)
    result = await db.execute(
        select(TenantTheme)
        .where(TenantTheme.tenant_id == tenant_id)
        .order_by(TenantTheme.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("", response_model=ThemeResponseWithEmail, dependencies=[Depends(verify_admin_key)])
async def upsert_theme(request: Request, theme_in: ThemeCreate, tenant_id: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    tenant, tenant_id = await _get_tenant_context(request, db, tenant_id)

    if theme_in.authentik_app_slug:
        stmt = select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == theme_in.authentik_flow_slug,
            TenantTheme.authentik_app_slug == theme_in.authentik_app_slug
        )
    else:
        stmt = select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == theme_in.authentik_flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        )

    result = await db.execute(stmt)
    existing_theme = result.scalar_one_or_none()

    if existing_theme:
        for field, value in theme_in.model_dump().items():
            setattr(existing_theme, field, value)
        db.add(existing_theme)
        db_theme = existing_theme
    else:
        db_theme = TenantTheme(**theme_in.model_dump(), tenant_id=tenant_id)
        db.add(db_theme)

    await db.flush()
    await db.commit()
    await db.refresh(db_theme)

    await _update_authentik_scope_descriptions(db_theme.expansion_config)

    await cache.delete(f"theme:{db_theme.authentik_flow_slug}:global")
    if db_theme.authentik_app_slug:
        await cache.delete(f"theme:{db_theme.authentik_flow_slug}:{db_theme.authentik_app_slug}")
    if cache.redis:
        try:
            keys = await cache.redis.keys(f"theme:{db_theme.authentik_flow_slug}:*")
            if keys:
                await cache.redis.delete(*keys)
        except Exception:
            pass

    email_bodies = await _load_email_bodies(db_theme.authentik_flow_slug, tenant_id, db)
    return _build_theme_response_with_email(db_theme, email_bodies)


def _strip_html_tags(text: str) -> str:
    return re.sub(r'<[^>]+>', ' ', text or '').strip()


@router.get("/{flow_slug}/emails/preview/{event_type}", dependencies=[Depends(verify_admin_key)])
async def preview_email(
    request: Request,
    flow_slug: str,
    event_type: str,
    app_slug: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    tenant, tenant_id = await _get_tenant_context(request, db)

    if event_type not in EMAIL_EVENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event_type. Must be one of: {sorted(EMAIL_EVENT_TYPES)}"
        )

    # Intentar tema específico de la app; si no existe, caer al global
    theme = None
    if app_slug:
        result = await db.execute(
            select(TenantTheme).where(
                TenantTheme.tenant_id == tenant_id,
                TenantTheme.authentik_flow_slug == flow_slug,
                TenantTheme.authentik_app_slug == app_slug
            )
        )
        theme = result.scalar_one_or_none()

    if theme is None:
        result = await db.execute(
            select(TenantTheme).where(
                TenantTheme.tenant_id == tenant_id,
                TenantTheme.authentik_flow_slug == flow_slug,
                TenantTheme.authentik_app_slug.is_(None)
            )
        )
        theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme not found for flow '{flow_slug}'.")

    eb_result = await db.execute(
        select(TenantEmailBody).where(
            TenantEmailBody.tenant_id == tenant_id,
            TenantEmailBody.flow_slug == flow_slug,
            TenantEmailBody.event_type == event_type
        )
    )
    email_body = eb_result.scalar_one_or_none()
    # Raw body from DB (may be empty — template provides defaults in that case)
    body_html = email_body.body_html if email_body else ''
    subject = email_body.subject if email_body else ''

    # Nombre legible del tenant: strip HTML de system_name ("CASMARTS<br>Core" → "CASMARTS Core")
    tenant_name = _strip_html_tags(theme.system_name) or theme.display_name or 'CASMARTS'

    # Logos para correos: se prefiere una URL pública (mejor compatibilidad con
    # Outlook, que bloquea/rompe imágenes base64 embebidas) y se cae a base64
    # si por lo que sea la URL pública no resuelve para el destinatario.
    app_qs = f'?app={app_slug}' if app_slug else ''
    logo_url: Optional[str] = None
    logo_base64: Optional[str] = None

    # Prioridad: theme logo > tenant logo > None
    if theme.logo_top_base64:
        logo_url = f'{settings.PUBLIC_API_BASE_URL}/api/v1/public/theme/{flow_slug}/image/logo_top{app_qs}'
        logo_base64 = theme.logo_top_base64
    elif tenant.logo_email_base64:
        logo_base64 = tenant.logo_email_base64

    # Validar tamaño del fallback base64
    if logo_base64 and len(logo_base64.encode()) > 200 * 1024:
        log.warning("Logo >200 KB para flow '%s' — omitiendo del correo.", flow_slug)
        logo_base64 = None

    # Logo inferior (pie de página / "Plataforma de Administración"): misma lógica
    logo_bottom_url: Optional[str] = None
    logo_bottom_base64: Optional[str] = None
    if theme.logo_bottom_base64:
        logo_bottom_url = f'{settings.PUBLIC_API_BASE_URL}/api/v1/public/theme/{flow_slug}/image/logo_bottom{app_qs}'
        logo_bottom_base64 = theme.logo_bottom_base64
        if logo_bottom_base64 and len(logo_bottom_base64.encode()) > 200 * 1024:
            log.warning("logo_bottom_base64 >200 KB para flow '%s' — omitiendo del correo.", flow_slug)
            logo_bottom_base64 = None

    # Determinar el flow correcto según el evento. new_account usa el mismo
    # flow de recuperación de contraseña que password_reset: nunca se envía
    # una contraseña por correo, solo un enlace de un solo uso para
    # establecerla la primera vez (mandato de producto).
    flow_map = {
        'password_reset': 'password-recovery',
        'email_verification': 'default-source-enrollment',
        'new_account': 'password-recovery',
        'account_lockout': 'default-authentication-flow',
        'security_change': 'default-user-settings-flow',
        'account_locked_admin': 'default-authentication-flow',
        'account_unlocked_admin': 'default-authentication-flow',
        'login_success': 'default-authentication-flow',
        'suspicious_request': 'default-authentication-flow',
        'invitation_used': 'default-authentication-flow',
        'app_authorized': 'default-authentication-flow',
        'impersonation_started': 'default-user-settings-flow',
        'account_deleted': 'default-authentication-flow',
    }
    flow_slug = flow_map.get(event_type, 'default-authentication-flow')
    cta_url = f'https://auth.casmart.internal/if/flow/{flow_slug}/'

    client_ip_preview = request.client.host if request.client else '192.168.1.100'
    user_agent_preview = request.headers.get('user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

    html = render_event_email_html(
        theme=theme,
        tenant=tenant,
        event_type=event_type,
        body_html=body_html,
        subject=subject,
        logo_base64=logo_base64,
        logo_url=logo_url,
        logo_bottom_base64=logo_bottom_base64,
        logo_bottom_url=logo_bottom_url,
        cta_url=cta_url,
        tenant_name=tenant_name,
        substitution_values={
            'usuario_login': username or 'usuario.ejemplo',
            'usuario_email': user_email or 'usuario@casmarts.internal',
            'nombre_usuario': 'Usuario Ejemplo',
            'nombre_usuario_nombre': 'Usuario',
            'nombre_usuario_apellido': 'Ejemplo',
            'ip_origen': client_ip_preview,
            'navegador': user_agent_preview[:80],
            'dispositivo': 'Windows',
            'token': 'TOK-PREVIEW-12345',
            'realizado_por': 'Usuario: Usuario Ejemplo',
            'aplicacion_nombre': 'Aplicación CaSmarts',
            'aplicacion_slug': 'default',
        },
    )

    return HTMLResponse(content=html)


@router.get("/{flow_slug}/emails/default-body/{event_type}", dependencies=[Depends(verify_admin_key)])
async def get_default_email_body(
    request: Request,
    flow_slug: str,
    event_type: str,
    app_slug: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve el asunto y cuerpo HTML por defecto (definidos en el .j2 del evento)
    ya renderizados — para precargar el editor cuando el tenant aún no ha
    personalizado ese evento. Las variables {{ }} se dejan literales a propósito
    (se sustituyen en preview/envío), solo se resuelven las [[ ]] de Jinja real.
    """
    if event_type not in EMAIL_EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid event_type. Must be one of: {sorted(EMAIL_EVENT_TYPES)}")

    tenant, tenant_id = await _get_tenant_context(request, db)

    theme = None
    if app_slug:
        result = await db.execute(select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug == app_slug
        ))
        theme = result.scalar_one_or_none()
    if theme is None:
        result = await db.execute(select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        ))
        theme = result.scalar_one_or_none()
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme not found for flow '{flow_slug}'.")

    tenant_name = _strip_html_tags(theme.system_name) or theme.display_name or 'CASMARTS'

    env = _build_email_jinja2_env()
    source, _, _ = env.loader.get_source(env, f'{event_type}.html.j2')

    subject_match = re.search(r"set\s+subject\s*=\s*subject\s+or\s+'([^']*)'", source)
    default_subject = subject_match.group(1) if subject_match else ''

    body_match = re.search(r"\[%\s*set\s+body_html\s*%\](.*?)\[%-?\s*endset\s*%\]", source, re.S)
    default_body_raw = body_match.group(1) if body_match else ''

    frag_env = Environment(variable_start_string='[[', variable_end_string=']]', autoescape=False)
    default_body = frag_env.from_string(default_body_raw).render(tenant_name=tenant_name).strip()

    return {"subject": default_subject, "body_html": default_body}


class TestEmailRequest(BaseModel):
    to_email: str
    event_type: str
    app_slug: Optional[str] = None
    # Por defecto el nombre se adivina del local-part del email
    # (israel.martinez@... → "Israel Martinez") — sirve para direcciones
    # reales tipo nombre.apellido@empresa.com, pero da un nombre sin
    # sentido para buzones personales (imarthe@hotmail.com → "Imarthe").
    # Este override deja probar con el nombre real sin cambiar el correo
    # de destino.
    display_name: Optional[str] = None

    @field_validator('to_email', mode='after')
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Dirección de correo inválida')
        return v


def _b64_to_bytes(data_url: str) -> tuple[bytes, str]:
    m = re.match(r'data:([^;]+);base64,(.+)', data_url or '', re.S)
    if m:
        return base64.b64decode(m.group(2)), m.group(1)
    return b'', 'image/png'


def _strip_header_injection(value: str) -> str:
    """Elimina CR/LF y caracteres de control para prevenir inyección de
    cabeceras SMTP (CWE-93) vía subject/to_email construidos a partir de
    datos que, aunque validados con regex, pueden originarse en HTML
    editado por el usuario (ej. <title> del cuerpo del correo)."""
    return re.sub(r'[\r\n\x00-\x08\x0b\x0c\x0e-\x1f]', '', value or '').strip()


def _send_smtp(
    to_email: str,
    subject: str,
    html: str,
    logo_bytes: bytes,
    logo_mime: str,
    logo_bottom_bytes: bytes = b'',
    logo_bottom_mime: str = 'image/png',
) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        raise ValueError("SMTP no configurado — añadir SMTP_HOST, SMTP_USER y SMTP_PASSWORD al .env")

    to_email = _strip_header_injection(to_email)
    subject = _strip_header_injection(subject)

    # El HTML renderiza <img src="https://.../image/logo_top|logo_bottom...">
    # (URL pública) — aquí se reemplaza por cid: y se adjunta inline, para no
    # depender de que el cliente de correo del destinatario pueda resolver esa
    # URL (más confiable que la URL pública sola, y evita el bloqueo que
    # Outlook aplica a imágenes base64 embebidas directo en el HTML).
    CID_TOP = 'logo_casmarts_top_cid'
    CID_BOTTOM = 'logo_casmarts_bottom_cid'
    if logo_bytes:
        html = re.sub(r'src="https://[^"]*logo_top[^"]*"', f'src="cid:{CID_TOP}"', html)
    if logo_bottom_bytes:
        html = re.sub(r'src="https://[^"]*logo_bottom[^"]*"', f'src="cid:{CID_BOTTOM}"', html)

    outer = MIMEMultipart('related')
    outer['Subject'] = subject
    outer['From'] = f'CASMARTS Core <{settings.SMTP_FROM or settings.SMTP_USER}>'
    outer['To'] = to_email

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(html, 'html', 'utf-8'))
    outer.attach(alt)

    if logo_bytes:
        subtype = logo_mime.split('/')[-1] if '/' in logo_mime else 'png'
        img = MIMEImage(logo_bytes, _subtype=subtype)
        img.add_header('Content-ID', f'<{CID_TOP}>')
        img.add_header('Content-Disposition', 'inline', filename=f'logo_top.{subtype}')
        outer.attach(img)

    if logo_bottom_bytes:
        subtype = logo_bottom_mime.split('/')[-1] if '/' in logo_bottom_mime else 'png'
        img = MIMEImage(logo_bottom_bytes, _subtype=subtype)
        img.add_header('Content-ID', f'<{CID_BOTTOM}>')
        img.add_header('Content-Disposition', 'inline', filename=f'logo_bottom.{subtype}')
        outer.attach(img)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as srv:
        srv.ehlo()
        if settings.SMTP_TLS:
            srv.starttls(context=ctx)
        srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        srv.sendmail(settings.SMTP_FROM or settings.SMTP_USER, [to_email], outer.as_string())


def _format_link_expiry_text(minutes: int) -> str:
    """Texto legible para el enlace de un solo uso (password_reset/new_account),
    a partir de password_policies.link_expiry_minutes — evita que el correo
    diga un valor fijo ("1 hora") que se desincronice del token_expiry real
    configurado en Authentik (ver password_policy.py:_push_to_authentik)."""
    if minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} hora" + ("s" if hours != 1 else "")
    return f"{minutes} minuto" + ("s" if minutes != 1 else "")


async def _get_link_expiry_minutes(db: AsyncSession) -> int:
    from app.models.password_policy import PasswordPolicy, SINGLETON_ID
    result = await db.execute(select(PasswordPolicy).where(PasswordPolicy.id == SINGLETON_ID))
    policy = result.scalar_one_or_none()
    return policy.link_expiry_minutes if policy else 60


def render_event_email_html(
    theme: TenantTheme,
    tenant: Tenant,
    event_type: str,
    body_html: str,
    subject: str,
    logo_base64: Optional[str],
    logo_url: Optional[str],
    logo_bottom_base64: Optional[str],
    logo_bottom_url: Optional[str],
    cta_url: str,
    tenant_name: str,
    substitution_values: dict,
) -> str:
    """
    Renderiza el wrapper Jinja de un evento + sustituye las variables {{ }}.
    Compartido por send_test_email (datos de prueba) y por el receptor de
    eventos reales de Authentik (datos reales del webhook) — un solo lugar
    para la lógica de render, evita que ambos caminos se desincronicen.

    `substitution_values` acepta las claves: usuario_login, usuario_email,
    nombre_usuario, nombre_usuario_nombre, nombre_usuario_apellido,
    ip_origen, navegador, dispositivo, fecha_evento, fecha_hora_cambio,
    realizado_por, aplicacion_nombre, aplicacion_slug, rol_asignado, token.
    Las que no se pasen quedan vacías o con su default razonable — mejor que
    inventar un dato falso en un correo real.
    """
    env_j2 = _build_email_jinja2_env()
    tmpl = env_j2.get_template(f'{event_type}.html.j2')
    html = tmpl.render(
        theme=theme,
        body_html=body_html,
        subject=subject,
        logo_base64=logo_base64,
        logo_url=logo_url,
        logo_bottom_base64=logo_bottom_base64,
        logo_bottom_url=logo_bottom_url,
        event_type=event_type,
        cta_url=cta_url,
        tenant_name=tenant_name,
    )

    import datetime
    current_year = datetime.datetime.now().year
    sv = substitution_values
    substitutions = {
        '{{ url }}': cta_url,
        '{{url_acceso}}': cta_url,
        '{{ user.username }}': sv.get('usuario_login', ''),
        '{{usuario_login}}': sv.get('usuario_login', ''),
        '{{ user.email }}': sv.get('usuario_email', ''),
        '{{usuario_email}}': sv.get('usuario_email', ''),
        '{{nombre_usuario}}': sv.get('nombre_usuario', ''),
        '{{nombre_usuario_nombre}}': sv.get('nombre_usuario_nombre', ''),
        '{{nombre_usuario_apellido}}': sv.get('nombre_usuario_apellido', ''),
        '{{ tenant.name }}': tenant_name,
        '{{nombre_sistema}}': tenant_name,
        '{{aplicacion_nombre}}': sv.get('aplicacion_nombre', 'Aplicación CaSmarts'),
        '{{aplicacion_slug}}': sv.get('aplicacion_slug', 'default'),
        '{{ip_origen}}': sv.get('ip_origen', 'No disponible'),
        '{{navegador}}': sv.get('navegador', 'No disponible'),
        '{{dispositivo}}': sv.get('dispositivo', 'No disponible'),
        '{{ token }}': sv.get('token', ''),
        '{{fecha_evento}}': sv.get('fecha_evento') or datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
        '{{fecha_hora_cambio}}': sv.get('fecha_hora_cambio') or datetime.datetime.now().isoformat(),
        '{{anio}}': str(current_year),
        '{{empresa_nombre}}': tenant.name,
        '{{contacto_soporte}}': 'soporte@casmarts.internal',
        '{{realizado_por}}': sv.get('realizado_por', ''),
        '{{footer_legal}}': 'Este mensaje es confidencial y para uso exclusivo del destinatario. Si lo recibiste por error, notifícalo y elimínalo.',
        '{{rol_asignado}}': sv.get('rol_asignado', 'Usuario estándar'),
        '{{color_primario}}': theme.primary_color or '#4272A5',
        '{{logo_url}}': logo_url or '',
        '{{enlace_expiracion_texto}}': sv.get('enlace_expiracion_texto') or _format_link_expiry_text(60),
    }
    for var, val in substitutions.items():
        html = html.replace(var, val)
    return html


@router.post("/{flow_slug}/emails/test", dependencies=[Depends(verify_admin_key)])
async def send_test_email(
    request: Request,
    flow_slug: str,
    body: TestEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    tenant, tenant_id = await _get_tenant_context(request, db)

    if body.event_type not in EMAIL_EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"event_type inválido: {body.event_type}")

    # Resolver tema (app-específico con fallback a global)
    theme = None
    if body.app_slug:
        r = await db.execute(select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug == body.app_slug
        ))
        theme = r.scalar_one_or_none()
    if theme is None:
        r = await db.execute(select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        ))
        theme = r.scalar_one_or_none()
    if not theme:
        raise HTTPException(status_code=404, detail=f"Tema no encontrado para flow '{flow_slug}'.")

    # Cuerpo del correo desde BD (vacío → usa defaults del template)
    eb = await db.execute(select(TenantEmailBody).where(
        TenantEmailBody.tenant_id == tenant_id,
        TenantEmailBody.flow_slug == flow_slug,
        TenantEmailBody.event_type == body.event_type
    ))
    email_body = eb.scalar_one_or_none()
    db_body_html = email_body.body_html if email_body else ''
    db_subject = email_body.subject if email_body else ''

    tenant_name = _strip_html_tags(theme.system_name) or theme.display_name or 'CASMARTS'

    # Logo superior: URL pública (se adjunta inline vía CID en _send_smtp) +
    # base64 como respaldo si el render/preview no pasa por _send_smtp.
    app_qs = f'?app={body.app_slug}' if body.app_slug else ''
    logo_bytes, logo_mime = b'', 'image/png'
    logo_base64: Optional[str] = None
    logo_url: Optional[str] = None
    if theme.logo_top_base64:
        logo_bytes, logo_mime = _b64_to_bytes(theme.logo_top_base64)
        logo_base64 = theme.logo_top_base64
        if len(logo_bytes) > 200 * 1024:
            log.warning("Logo superior >200 KB para flow '%s' — omitido del correo de prueba.", flow_slug)
            logo_bytes = b''
            logo_base64 = None
        else:
            logo_url = f'{settings.PUBLIC_API_BASE_URL}/api/v1/public/theme/{flow_slug}/image/logo_top{app_qs}'

    # Logo inferior (pie de página / "Plataforma de Administración")
    logo_bottom_bytes, logo_bottom_mime = b'', 'image/png'
    logo_bottom_base64: Optional[str] = None
    logo_bottom_url: Optional[str] = None
    if theme.logo_bottom_base64:
        if len(theme.logo_bottom_base64.encode()) > 200 * 1024:
            log.warning("Logo inferior >200 KB para flow '%s' — omitido del correo de prueba.", flow_slug)
        else:
            logo_bottom_bytes, logo_bottom_mime = _b64_to_bytes(theme.logo_bottom_base64)
            logo_bottom_base64 = theme.logo_bottom_base64
            logo_bottom_url = f'{settings.PUBLIC_API_BASE_URL}/api/v1/public/theme/{flow_slug}/image/logo_bottom{app_qs}'

    # Determinar el flow correcto según el evento. new_account usa el mismo
    # flow de recuperación de contraseña que password_reset: nunca se envía
    # una contraseña por correo, solo un enlace de un solo uso para
    # establecerla la primera vez (mandato de producto).
    flow_map = {
        'password_reset': 'password-recovery',
        'email_verification': 'default-source-enrollment',
        'new_account': 'password-recovery',
        'account_lockout': 'default-authentication-flow',
        'security_change': 'default-user-settings-flow',
        'account_locked_admin': 'default-authentication-flow',
        'account_unlocked_admin': 'default-authentication-flow',
        'login_success': 'default-authentication-flow',
        'suspicious_request': 'default-authentication-flow',
        'invitation_used': 'default-authentication-flow',
        'app_authorized': 'default-authentication-flow',
        'impersonation_started': 'default-user-settings-flow',
        'account_deleted': 'default-authentication-flow',
    }
    cta_url_flow = flow_map.get(body.event_type, 'default-authentication-flow')
    cta_url = f'https://auth.casmart.internal/if/flow/{cta_url_flow}/'

    # Extraer información del contexto de la solicitud
    client_ip = request.client.host if request.client else '127.0.0.1'
    user_agent = request.headers.get('user-agent', 'No disponible')

    # Extraer información del navegador desde user-agent
    def parse_device_from_ua(ua: str) -> str:
        if 'Windows' in ua:
            return 'Windows'
        elif 'Mac' in ua:
            return 'macOS'
        elif 'Linux' in ua:
            return 'Linux'
        elif 'Android' in ua:
            return 'Android'
        elif 'iPhone' in ua or 'iPad' in ua:
            return 'iOS'
        return 'Desconocido'

    device = parse_device_from_ua(user_agent)

    # Datos del usuario (desde email de prueba, o el override si se dio uno)
    user_email = str(body.to_email)
    user_login = user_email.split('@')[0]
    user_name_full = (body.display_name or '').strip() or user_login.replace('.', ' ').title()  # israelm.martinez → Israelm Martinez
    user_name_parts = user_name_full.split()
    user_name_first = user_name_parts[0] if len(user_name_parts) > 0 else ''
    user_name_last = ' '.join(user_name_parts[1:]) if len(user_name_parts) > 1 else ''

    # Nombre de la aplicación (si se proporcionó)
    app_name = 'Aplicación CaSmarts'
    if body.app_slug:
        app_name = body.app_slug.replace('-', ' ').title()

    link_expiry_minutes = await _get_link_expiry_minutes(db)

    html = render_event_email_html(
        theme=theme,
        tenant=tenant,
        event_type=body.event_type,
        body_html=db_body_html,
        subject=db_subject,
        logo_base64=logo_base64,
        logo_url=logo_url,
        logo_bottom_base64=logo_bottom_base64,
        logo_bottom_url=logo_bottom_url,
        cta_url=cta_url,
        tenant_name=tenant_name,
        substitution_values={
            'usuario_login': user_login,
            'usuario_email': user_email,
            'nombre_usuario': user_name_full,
            'nombre_usuario_nombre': user_name_first,
            'nombre_usuario_apellido': user_name_last,
            'ip_origen': client_ip,
            'navegador': user_agent[:80],
            'dispositivo': device,
            'token': 'TOK-PREVIEW-12345',
            'realizado_por': f'Usuario: {user_name_full}',
            'aplicacion_nombre': app_name,
            'aplicacion_slug': body.app_slug or 'default',
            'enlace_expiracion_texto': _format_link_expiry_text(link_expiry_minutes),
        },
    )

    subject_line = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    subject_text = f'[TEST] {subject_line.group(1).strip()}' if subject_line else f'[TEST] Correo de prueba'

    try:
        _send_smtp(str(body.to_email), subject_text, html, logo_bytes, logo_mime, logo_bottom_bytes, logo_bottom_mime)
    except Exception as e:
        log.error("Error enviando correo de prueba: %s", e)
        raise HTTPException(status_code=502, detail=f"Error SMTP: {str(e)}")

    return {"status": "sent", "to": str(body.to_email), "subject": subject_text}


# ─────────────────────────────────────────────────────────────────────────
# Prueba REAL vía Authentik — a diferencia de /emails/test (render local +
# SMTP directo), esto dispara el mecanismo real del evento en Authentik:
# EmailStage real, o un evento real (user_write/password_set/login_failed)
# que atraviesa el puente de webhooks tal como le pasaría a un usuario real.
# ─────────────────────────────────────────────────────────────────────────

_QA_TEST_USERNAME = "qa-email-test"
_QA_TEST_EMAIL = "qa-email-test@casmarts.internal"


class TestRealEmailRequest(BaseModel):
    event_type: str
    # Requerido para password_reset/email_verification (usuario existente
    # al que se le manda el enlace real) y para account_lockout (usuario al
    # que se le van a provocar intentos fallidos REALES). No se usa para
    # new_account/security_change — esos usan un usuario descartable propio
    # (qa-email-test) para no tocar una cuenta real.
    username: Optional[str] = None


def _authentik_headers() -> dict:
    if not settings.AUTHENTIK_API_TOKEN or not settings.AUTHENTIK_HOST:
        raise HTTPException(status_code=503, detail="AUTHENTIK_API_TOKEN/AUTHENTIK_HOST no configurados en .env.")
    return {"Authorization": f"Bearer {settings.AUTHENTIK_API_TOKEN}"}


async def _authentik_get_user_by_username(client: httpx.AsyncClient, username: str) -> Optional[dict]:
    resp = await client.get(
        f"{settings.AUTHENTIK_HOST}/api/v3/core/users/",
        headers=_authentik_headers(),
        params={"username": username},
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0] if results else None


async def _authentik_create_qa_test_user(client: httpx.AsyncClient) -> dict:
    resp = await client.post(
        f"{settings.AUTHENTIK_HOST}/api/v3/core/users/",
        headers=_authentik_headers(),
        json={
            "username": _QA_TEST_USERNAME,
            "name": "QA Email Test",
            "email": _QA_TEST_EMAIL,
            "is_active": True,
            "path": "qa-testing",
        },
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Authentik rechazó la creación del usuario de prueba: {resp.text[:300]}")
    return resp.json()


async def _authentik_get_email_stage_pk(client: httpx.AsyncClient, stage_name: str) -> str:
    resp = await client.get(f"{settings.AUTHENTIK_HOST}/api/v3/stages/email/", headers=_authentik_headers())
    resp.raise_for_status()
    stage = next((s for s in resp.json().get("results", []) if s.get("name") == stage_name), None)
    if not stage:
        raise HTTPException(status_code=502, detail=f"No se encontró el EmailStage '{stage_name}' en Authentik.")
    return stage["pk"]


async def _trigger_real_failed_logins(client: httpx.AsyncClient, username: str, attempts: int = 6) -> Optional[str]:
    """
    Provoca `attempts` intentos fallidos REALES vía el flow executor público
    de Authentik (default-authentication-flow), para ejercitar de punta a
    punta ReputationPolicy + casmarts-login-failed-matcher + el correo real
    de account_lockout.

    ADVERTENCIA: no se pudo verificar en vivo el protocolo exacto del flow
    executor en la sesión donde se escribió esto (bloqueo de permisos para
    experimentar contra la instancia real) — implementado según el patrón
    estándar documentado de Authentik (identification+password combinados
    en un solo POST porque default-authentication-identification tiene
    password_stage configurado, sesión vía cookies + CSRF). Probarlo contra
    una cuenta descartable antes de confiar en él para bloquear una cuenta
    real; si Authentik devuelve un shape distinto, ajustar aquí.

    Devuelve None si todos los intentos se enviaron sin error de transporte,
    o un mensaje de advertencia si alguno falló.
    """
    flow_url = f"{settings.AUTHENTIK_HOST}/api/v3/flows/executor/default-authentication-flow/"
    bogus_password = f"wrong-{secrets.token_urlsafe(8)}"
    last_error: Optional[str] = None
    for _ in range(attempts):
        try:
            init_resp = await client.get(flow_url, params={"query": ""})
            init_resp.raise_for_status()
            csrf_token = client.cookies.get("authentik_csrf") or client.cookies.get("csrftoken")
            post_headers = {"X-CSRFToken": csrf_token} if csrf_token else {}
            attempt_resp = await client.post(
                flow_url,
                headers=post_headers,
                json={"uid_field": username, "password": bogus_password},
            )
            if attempt_resp.status_code >= 400:
                last_error = attempt_resp.text[:300]
        except httpx.HTTPError as e:
            last_error = str(e)
    if last_error:
        log.warning("account_lockout real-test: al menos un intento contra el flow executor falló: %s", last_error)
    return last_error


@router.post("/{flow_slug}/emails/test-real", dependencies=[Depends(verify_admin_key)])
async def send_test_email_real(
    flow_slug: str,
    body: TestRealEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    if body.event_type not in EMAIL_EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"event_type inválido: {body.event_type}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        if body.event_type in ("password_reset", "email_verification"):
            if not body.username:
                raise HTTPException(status_code=422, detail="username es obligatorio para probar este tipo vía el flow real de Authentik.")
            from app.routers.email_sync import _AUTHENTIK_EMAIL_STAGES
            stage_info = _AUTHENTIK_EMAIL_STAGES.get(body.event_type)
            if not stage_info:
                raise HTTPException(status_code=400, detail=f"'{body.event_type}' no tiene un EmailStage real configurado.")
            stage_name, _ = stage_info
            user = await _authentik_get_user_by_username(client, body.username)
            if not user:
                raise HTTPException(status_code=404, detail=f"Usuario '{body.username}' no existe en Authentik.")
            stage_pk = await _authentik_get_email_stage_pk(client, stage_name)
            # recovery_email() de Authentik NO hereda EmailStage.token_expiry si
            # no se manda token_duration explícito — cae al default global del
            # tenant de Authentik (visto en vivo: minutes=30, no los 60 guardados
            # en Política de Contraseña, causando que el correo real mostrara
            # "expira 29 minutos" con la política guardando 60). El flujo real
            # de recuperación (stage.py) sí usa EmailStage.token_expiry
            # directamente porque no pasa por este endpoint de administración.
            link_expiry_minutes = await _get_link_expiry_minutes(db)
            resp = await client.post(
                f"{settings.AUTHENTIK_HOST}/api/v3/core/users/{user['pk']}/recovery_email/",
                headers=_authentik_headers(),
                json={"email_stage": stage_pk, "token_duration": f"minutes={link_expiry_minutes}"},
            )
            if resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Authentik rechazó el envío: {resp.text[:300]}")
            return {"status": "sent", "event_type": body.event_type, "mode": "real-authentik-flow", "to_user": body.username}

        if body.event_type in ("new_account", "security_change"):
            existing = await _authentik_get_user_by_username(client, _QA_TEST_USERNAME)
            if body.event_type == "new_account":
                # Recrear (borrar + crear) para forzar un user_write con
                # created=true real — solo editar el existente no dispararía
                # la señal que escucha casmarts-new-account-matcher.
                if existing:
                    del_resp = await client.delete(
                        f"{settings.AUTHENTIK_HOST}/api/v3/core/users/{existing['pk']}/",
                        headers=_authentik_headers(),
                    )
                    if del_resp.status_code >= 400 and del_resp.status_code != 404:
                        raise HTTPException(status_code=502, detail=f"No se pudo recrear el usuario de prueba: {del_resp.text[:300]}")
                await _authentik_create_qa_test_user(client)
            else:
                user = existing or await _authentik_create_qa_test_user(client)
                set_pw_resp = await client.post(
                    f"{settings.AUTHENTIK_HOST}/api/v3/core/users/{user['pk']}/set_password/",
                    headers=_authentik_headers(),
                    json={"password": secrets.token_urlsafe(24)},
                )
                if set_pw_resp.status_code >= 400:
                    raise HTTPException(status_code=502, detail=f"Authentik rechazó el cambio de password: {set_pw_resp.text[:300]}")
            return {"status": "triggered", "event_type": body.event_type, "mode": "real-authentik-event", "test_user": _QA_TEST_USERNAME}

        if body.event_type in ("account_locked_admin", "account_unlocked_admin"):
            user = await _authentik_get_user_by_username(client, _QA_TEST_USERNAME) or await _authentik_create_qa_test_user(client)
            target_active = body.event_type == "account_unlocked_admin"
            # Se pre-siembra el estado ANTERIOR (el opuesto) en Valkey antes
            # del PATCH — si no, la primera vez que se prueba este tipo de
            # evento, el webhook vería is_active sin un valor previo en
            # cache y solo fijaría la base sin avisar (ver
            # _resolve_admin_toggle_event en authentik_events.py).
            await cache.set(
                f"user_active_state:{user['pk']}",
                "0" if target_active else "1",
                ex=315360000,
            )
            patch_resp = await client.patch(
                f"{settings.AUTHENTIK_HOST}/api/v3/core/users/{user['pk']}/",
                headers=_authentik_headers(),
                json={"is_active": target_active},
            )
            if patch_resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Authentik rechazó el cambio de estado: {patch_resp.text[:300]}")
            return {"status": "triggered", "event_type": body.event_type, "mode": "real-authentik-event", "test_user": _QA_TEST_USERNAME}

        if body.event_type == "account_lockout":
            if not body.username:
                raise HTTPException(status_code=422, detail="username es obligatorio: se van a provocar intentos fallidos REALES contra esa cuenta.")
            warning = await _trigger_real_failed_logins(client, body.username, attempts=6)
            result = {
                "status": "triggered",
                "event_type": body.event_type,
                "mode": "real-authentik-event",
                "target_user": body.username,
                "note": "Se provocaron intentos fallidos reales — la cuenta probablemente quedó bloqueada de verdad.",
            }
            if warning:
                result["warning"] = warning
            return result

        raise HTTPException(status_code=400, detail=f"'{body.event_type}' no tiene un disparador de prueba real implementado.")


@router.get("/{flow_slug}", response_model=ThemeResponseWithEmail, dependencies=[Depends(verify_admin_key)])
async def get_theme(
    request: Request,
    flow_slug: str,
    app_slug: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    tenant, tenant_id = await _get_tenant_context(request, db)

    if app_slug:
        stmt = select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug == app_slug
        )
    else:
        stmt = select(TenantTheme).where(
            TenantTheme.tenant_id == tenant_id,
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        )
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow or app slug.")

    email_bodies = await _load_email_bodies(flow_slug, tenant_id, db)
    return _build_theme_response_with_email(db_theme, email_bodies)


@router.patch("/{flow_slug}", response_model=ThemeResponseWithEmail, dependencies=[Depends(verify_admin_key)])
async def patch_theme(
    request: Request,
    flow_slug: str,
    theme_in: ThemeUpdateWithEmail,
    db: AsyncSession = Depends(get_db)
):
    tenant, tenant_id = await _get_tenant_context(request, db)

    stmt = select(TenantTheme).where(
        TenantTheme.tenant_id == tenant_id,
        TenantTheme.authentik_flow_slug == flow_slug
    )
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow slug.")

    update_data = theme_in.model_dump(exclude_unset=True)
    email_bodies_data = update_data.pop('email_bodies', None)

    for field, value in update_data.items():
        setattr(db_theme, field, value)

    db.add(db_theme)

    if email_bodies_data:
        bodies = {k: EmailBodySchema(**v) for k, v in email_bodies_data.items()}
        await _upsert_email_bodies(flow_slug, tenant_id, bodies, db)

    await db.commit()
    await db.refresh(db_theme)

    await cache.delete(f"theme:{flow_slug}")
    if cache.redis:
        try:
            keys = await cache.redis.keys(f"theme:{flow_slug}:*")
            if keys:
                await cache.redis.delete(*keys)
        except Exception:
            pass

    email_bodies = await _load_email_bodies(flow_slug, tenant_id, db)
    return _build_theme_response_with_email(db_theme, email_bodies)


@router.delete("/{flow_slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_key)])
async def delete_theme(request: Request, flow_slug: str, db: AsyncSession = Depends(get_db)):
    tenant, tenant_id = await _get_tenant_context(request, db)

    stmt = select(TenantTheme).where(
        TenantTheme.tenant_id == tenant_id,
        TenantTheme.authentik_flow_slug == flow_slug
    )
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow slug.")

    await db.delete(db_theme)
    await db.commit()
    await cache.delete(f"theme:{flow_slug}")


# ── login template machinery ─────────────────────────────────────────────────

_DEFAULT_THEME = SimpleNamespace(
    primary_color='#4272A5',
    hover_color='#2d5580',
    card_bg_color='#FFFFFF',
    panel_bg_color='#F6F9FD',
    bg_type='gradient',
    bg_flat_color=None,
    bg_gradient_from='#c8c4bc',
    bg_gradient_to='#a09890',
    bg_image_base64=None,
    bg_opacity=1.0,
    form_opacity=0.55,
    form_height_pct=None,
    logos_opacity=0.55,
    logos_height_pct=None,
    layout_position='left',
    name_align='center',
    subtitle_align='center',
    privacy_align='center',
    system_name='CASMARTS<br>Core',
    system_subtitle='Portal Institucional',
    logo_top_base64=None,
    logo_bottom_base64=None,
    logo_top_text=None,
    logo_bottom_text=None,
    privacy_pdf_url=None,
    display_name='CASMARTS',
    allow_self_registration=False,
    show_social_google=False,
    show_social_microsoft=False,
    show_social_gov_id=False,
    show_forgot_password=True,
    show_logos_panel=True,
    show_password_toggle=True,
    show_system_name=True,
    show_system_subtitle=True,
    show_field_labels=True,
    show_app_message=False,
    email_footer_text=None,
    email_template_type='integrated',
    custom_messages={},
)


def _hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip('#')
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    except (ValueError, IndexError):
        return "255, 255, 255"


def _build_jinja2_env() -> Environment:
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        variable_start_string="[[",
        variable_end_string="]]",
        block_start_string="[%",
        block_end_string="%]",
        comment_start_string="[#",
        comment_end_string="#]",
        autoescape=False,
    )
    env.filters["hex_to_rgb"] = _hex_to_rgb
    return env


def _build_email_jinja2_env() -> Environment:
    email_dir = Path(__file__).parent.parent / "templates" / "email"
    env = Environment(
        loader=FileSystemLoader(str(email_dir)),
        variable_start_string="[[",
        variable_end_string="]]",
        block_start_string="[%",
        block_end_string="%]",
        comment_start_string="[#",
        comment_end_string="#]",
        autoescape=False,
    )
    env.filters["hex_to_rgb"] = _hex_to_rgb
    return env


def _render_theme(env: Environment, theme) -> str:
    flow_slug = getattr(theme, 'authentik_flow_slug', 'default-authentication-flow') or 'default-authentication-flow'
    app_slug  = getattr(theme, 'authentik_app_slug', None) or ''
    app_qs    = f'?app={app_slug}' if app_slug else ''
    api_base  = '/lm'

    template = env.get_template("login.html.j2")
    import json
    custom_messages = getattr(theme, 'custom_messages', None) or {}
    # json.dumps no escapa '<'/'>'/'&' — sin esto, un valor conteniendo
    # "</script>" cierra el <script> real de login.html.j2 anticipadamente y
    # el contenido siguiente se ejecuta como HTML/JS (ver auditoría 2026-07-06).
    # Es la técnica estándar para embeber JSON dentro de un bloque <script>.
    custom_messages_json = (
        json.dumps(custom_messages)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return template.render(
        theme=theme,
        api_base=api_base,
        logo_top_url=f'{api_base}/api/v1/public/theme/{flow_slug}/image/logo_top{app_qs}' if getattr(theme, 'logo_top_base64', None) else '',
        logo_bottom_url=f'{api_base}/api/v1/public/theme/{flow_slug}/image/logo_bottom{app_qs}' if getattr(theme, 'logo_bottom_base64', None) else '',
        bg_image_url=f'{api_base}/api/v1/public/theme/{flow_slug}/image/bg_image{app_qs}' if getattr(theme, 'bg_image_base64', None) else '',
        custom_messages_json=custom_messages_json,
    )


def _build_universal_template(
    app_themes: list[tuple[str, TenantTheme]],
    global_theme,
) -> str:
    env = _build_jinja2_env()
    fallback = global_theme if global_theme else (app_themes[0][1] if app_themes else _DEFAULT_THEME)
    return _render_theme(env, fallback)


async def _sync_password_toggle(flow_slug: str, allow_show_password: bool) -> tuple[bool, Optional[str]]:
    """Alinea el botón nativo de 'mostrar contraseña' de Authentik con
    `theme.show_password_toggle`.

    El mecanismo anterior intentaba ocultar/mostrar el botón vía CSS
    (`.pf-c-input-group>.pf-c-button` en login.html.j2) — no puede funcionar:
    el campo de contraseña real es el web component Lit `ak-flow-input-password`,
    que vive en un Shadow DOM. Un <style> inyectado en el light DOM no cruza
    ese límite, así que el CSS nunca alcanzaba el botón real (verificado
    leyendo el bundle de Authentik 2026.2.4: `renderVisibilityToggle(){if(!this.allowShowPassword)return nothing;...}`).
    El botón solo existe en absoluto si `PasswordStage.allow_show_password`
    es True del lado de Authentik — hay que ajustar ese campo real vía API.

    Un PasswordStage puede estar vinculado a varios flows (`flow_set`); se
    filtra por el flow_slug del tema y se actualizan solo los stages
    realmente usados por ese flujo.
    """
    if not settings.AUTHENTIK_API_TOKEN or not settings.AUTHENTIK_HOST:
        return False, "AUTHENTIK_API_TOKEN/AUTHENTIK_HOST no configurados en .env."

    headers = {"Authorization": f"Bearer {settings.AUTHENTIK_API_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.AUTHENTIK_HOST}/api/v3/stages/password/", headers=headers)
            resp.raise_for_status()
            stages = resp.json().get("results", [])
            matching = [s for s in stages if any(f.get("slug") == flow_slug for f in s.get("flow_set", []))]
            if not matching:
                return False, f"No se encontró ninguna etapa de contraseña vinculada al flujo '{flow_slug}'."

            for stage in matching:
                if stage.get("allow_show_password") == allow_show_password:
                    continue
                patch_resp = await client.patch(
                    f"{settings.AUTHENTIK_HOST}/api/v3/stages/password/{stage['pk']}/",
                    headers=headers,
                    json={"allow_show_password": allow_show_password},
                )
                patch_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return False, f"Error de la API de Authentik: {e.response.text[:300]}"
    except httpx.RequestError as e:
        return False, f"No se pudo contactar a Authentik: {str(e)}"

    return True, None


@router.post("/{flow_slug}/deploy", dependencies=[Depends(verify_admin_key)])
async def deploy_theme(flow_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TenantTheme).where(TenantTheme.authentik_flow_slug == flow_slug)
    )
    themes: list[TenantTheme] = result.scalars().all()
    if not themes:
        raise HTTPException(status_code=404, detail="No themes found for this flow slug.")

    global_theme = next((t for t in themes if t.authentik_app_slug is None), None)
    app_themes = [(t.authentik_app_slug, t) for t in themes if t.authentik_app_slug]

    try:
        universal_html = _build_universal_template(app_themes, global_theme)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template build error: {str(e)}")

    output_dir = Path("/shared/authentik/templates/if")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "flow.html"
        output_path.write_text(universal_html, encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot write to shared volume: {str(e)}. Mount '../core-casmarts/data/authentik/custom-templates'.",
        )

    await cache.delete(f"theme:{flow_slug}:global")
    for _, theme in app_themes:
        if theme.authentik_app_slug:
            await cache.delete(f"theme:{flow_slug}:{theme.authentik_app_slug}")
    if cache.redis:
        try:
            keys = await cache.redis.keys(f"theme:{flow_slug}:*")
            if keys:
                await cache.redis.delete(*keys)
        except Exception:
            pass

    show_password_toggle = (
        global_theme.show_password_toggle if global_theme
        else (app_themes[0][1].show_password_toggle if app_themes else True)
    )
    password_toggle_synced, password_toggle_error = await _sync_password_toggle(flow_slug, show_password_toggle)
    if not password_toggle_synced:
        log.warning("No se pudo sincronizar el botón de mostrar contraseña para '%s': %s", flow_slug, password_toggle_error)

    deployed_apps = [slug for slug, _ in app_themes] or (["(global)"] if global_theme else [])
    return {
        "status": "deployed",
        "path": str(output_path),
        "apps": deployed_apps,
        "password_toggle_synced": password_toggle_synced,
        "password_toggle_error": password_toggle_error,
    }


# ── tenant resolver router ───────────────────────────────────────────────────

tenant_router = APIRouter(prefix="/api/v1/tenant", tags=["Tenant"])


@tenant_router.get("/resolve")
async def resolve_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint público para que frontend sepa qué tenant le corresponde.
    INPUT header: X-Tenant-Domain o se infiere del hostname
    OUTPUT: { tenant_id, tenant_name, domain_pattern, primary_color, secondary_color }
    """
    hostname = (
        request.headers.get("X-Tenant-Domain")
        or request.headers.get("X-Forwarded-Host")
        or (request.client.host if request.client else "localhost")
    )

    try:
        tenant, tenant_id = await _get_tenant_context(request, db)
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "domain_pattern": tenant.domain_pattern,
            "primary_color": tenant.primary_color,
            "secondary_color": tenant.secondary_color,
            "default_app_url": (tenant.config or {}).get("default_app_url"),
        }
    except Exception as e:
        log.warning(f"Error resolving tenant for '{hostname}': {e}")
        return {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "tenant_name": "CASMARTS Core",
            "domain_pattern": "casmarts.local",
            "primary_color": "#4272A5",
            "secondary_color": "#2d5580",
            "default_app_url": None,
        }


class TenantSettingsUpdate(BaseModel):
    default_app_url: Optional[str] = None

    @field_validator('default_app_url', mode='after')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == '':
            return None
        v = v.strip()
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('default_app_url debe ser una URL absoluta (http:// o https://)')
        return v


@tenant_router.get("/settings", dependencies=[Depends(verify_admin_key)])
async def get_tenant_settings(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Configuración a nivel tenant (no por tema/app) editable desde Vista
    General del designer — hoy solo default_app_url (a dónde se manda a un
    usuario no-admin que llega a /if/user/ sin una app específica en mente,
    ver custom_authentik.js).
    """
    tenant, _ = await _get_tenant_context(request, db)
    return {"default_app_url": (tenant.config or {}).get("default_app_url")}


@tenant_router.patch("/settings", dependencies=[Depends(verify_admin_key)])
async def update_tenant_settings(
    request: Request,
    body: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    tenant, _ = await _get_tenant_context(request, db)
    new_config = dict(tenant.config or {})
    new_config["default_app_url"] = body.default_app_url
    tenant.config = new_config
    await db.commit()
    return {"default_app_url": tenant.config.get("default_app_url")}


async def _sync_tenants_from_authentik(db: AsyncSession) -> None:
    """
    Sincroniza las marcas (brands) de Authentik hacia la tabla local de tenants.
    """
    try:
        async with authentik_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT brand_uuid, domain, branding_title FROM authentik_brands_brand")
            )
            authentik_brands = result.all()
            
        for brand in authentik_brands:
            brand_id, domain, name = brand
            
            stmt = select(Tenant).where(Tenant.id == brand_id)
            db_res = await db.execute(stmt)
            existing = db_res.scalar_one_or_none()
            
            if existing:
                existing.name = name
                existing.domain_pattern = domain
                db.add(existing)
            else:
                new_tenant = Tenant(
                    id=brand_id,
                    name=name,
                    domain_pattern=domain,
                    is_active=True,
                    primary_color="#4272A5",
                    secondary_color="#2d5580"
                )
                db.add(new_tenant)
                
        await db.commit()
    except Exception as e:
        log.error(f"Error syncing tenants from Authentik: {e}")


@tenant_router.get("/list")
async def list_available_tenants(db: AsyncSession = Depends(get_db)):
    """
    Lista todos los tenants activos disponibles.

    Útil para:
    - Selector de tenant en el frontend (desarrollo/testing)
    - Listar tenants para sincronización de emails
    - Administración de configuración multi-tenant

    Response:
    [
        {
            "tenant_id": "uuid",
            "tenant_name": "Nombre Tenant",
            "domain_pattern": "example.com",
            "primary_color": "#4272A5",
            "secondary_color": "#2d5580"
        }
    ]
    """
    try:
        await _sync_tenants_from_authentik(db)
        result = await db.execute(
            select(Tenant).where(Tenant.is_active == True).order_by(Tenant.name)
        )
        tenants = result.scalars().all()

        return [
            {
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name,
                "domain_pattern": tenant.domain_pattern,
                "primary_color": tenant.primary_color,
                "secondary_color": tenant.secondary_color,
            }
            for tenant in tenants
        ]
    except Exception as e:
        log.error(f"Error listing tenants: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch tenants"
        )


@router.get("/blueprint/download")
async def download_brand_blueprint(
    brand_name: str = Query(..., description="Nombre de la marca/brand"),
    domain: str = Query(..., description="Dominio de la marca")
):
    """
    Genera y descarga un Blueprint de Authentik para inicializar una nueva marca,
    aprovisionar sus dominios y la estructura de grupos de usuarios inicial.
    """
    brand_slug = brand_name.lower().replace(" ", "-").strip()
    yaml_content = f"""version: 1
metadata:
  name: Aprovisionamiento de Marca - {brand_name}
entries:
  # 1. Crear Marca (Brand) en Authentik
  - identifiers:
      domain: {domain}
    model: authentik_brands.brand
    attrs:
      name: {brand_name}
      domain: {domain}
      is_default: false
      branding_title: {brand_name} ID
      
  # 2. Crear Grupo Padre de la Marca (para usuarios de este dominio)
  - identifiers:
      name: {brand_name}-users
    model: authentik_core.group
    attrs:
      name: {brand_name}-users
      is_superuser: false

  # 3. Crear Subgrupos de aplicaciones bajo este Tenant/Marca
  - identifiers:
      name: {brand_name}-starter
    model: authentik_core.group
    attrs:
      name: {brand_name}-starter
      parent: !Find [authentik_core.group, [name, {brand_name}-users]]

  - identifiers:
      name: {brand_name}-plane
    model: authentik_core.group
    attrs:
      name: {brand_name}-plane
      parent: !Find [authentik_core.group, [name, {brand_name}-users]]
"""
    from fastapi.responses import Response
    return Response(
        content=yaml_content,
        media_type="text/yaml",
        headers={
            "Content-Disposition": f"attachment; filename=blueprint-brand-{brand_slug}.yaml"
        }
    )
