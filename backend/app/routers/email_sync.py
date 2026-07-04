import datetime
import logging
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.config import settings
from app.models.tenant import Tenant
from app.models.tenant_theme import TenantTheme
from app.routers.admin import verify_admin_key, _build_email_jinja2_env, _strip_html_tags

log = logging.getLogger(__name__)

email_sync_router = APIRouter(
    prefix="/api/v1/emails",
    tags=["Email Sync"],
    dependencies=[Depends(verify_admin_key)],
)

# event_type → (nombre del EmailStage real en Authentik, ruta del template
# desplegado). password_reset usa casmarts-smtp-gmail (flow
# password-recovery); email_verification usa casmarts-enrollment-verification
# (las 6 flows de enrollment, ver casmarts-email-verification.yaml). Los
# otros 3 tipos de correo (new_account, account_lockout, security_change) no
# tienen EmailStage propio — se resuelven vía el puente de eventos/webhook.
_AUTHENTIK_EMAIL_STAGES: dict[str, tuple[str, str]] = {
    "password_reset": ("casmarts-smtp-gmail", "email/password_reset.html"),
    "email_verification": ("casmarts-enrollment-verification", "email/email_verification.html"),
}

# Placeholders únicos usados durante el render de dos pasadas (Jinja + nuestra
# sustitución de {{variables}}) para que ninguno de los dos motores los
# interprete como propios — se convierten a tags Django reales al final.
_SENTINEL_URL = "§§AUTHENTIK_URL§§"
_SENTINEL_USER = "§§AUTHENTIK_USER§§"
_SENTINEL_EMAIL = "§§AUTHENTIK_EMAIL§§"
_SENTINEL_NOW = "§§AUTHENTIK_NOW§§"

# {% now %} solo, sin más, renderiza en la zona horaria ACTIVA de Django en
# el momento del request — que en Authentik es UTC por defecto, no la hora
# local del servidor (confirmado en producción 2026-07-02: correo mostró
# 21:57 con el servidor en 15:57 CST/America/Mexico_City). {% timezone %}
# fuerza la conversión sin tocar el TIME_ZONE global de Authentik (cambiar
# ese ajuste afectaría timestamps de todo el sistema, no solo el correo).
_DJANGO_NOW_LOCAL = '{% timezone "America/Mexico_City" %}{% now "d/m/Y H:i" %}{% endtimezone %}'


def _render_password_reset_for_authentik(theme: TenantTheme, tenant: Tenant) -> str:
    """
    Renderiza el evento password_reset como plantilla Django real para
    desplegar en Authentik. A diferencia de preview_email()/send_test_email(),
    el EmailStage de Authentik solo pasa {url, user, expires, token} al
    renderizar (confirmado leyendo authentik/stages/email/stage.py) — sin
    contexto de tenant/marca. Por eso todo lo demás (colores, logo, nombre,
    footer) se resuelve AHORA, a valores concretos de este tema; solo esos
    campos quedan como tags Django reales para que Authentik los rellene en
    cada envío real.

    Limitaciones respecto al preview/prueba (impuestas por lo que Authentik
    expone, no por elección): sin IP de origen (se omite esa fila de la
    tabla) y la vigencia del enlace usa `{{ expires|naturaltime }}` real del
    EmailStage en vez del "24 horas" fijo del texto de preview.
    """
    tenant_name = _strip_html_tags(theme.system_name) or theme.display_name or "CASMARTS"

    # Base64 embebido, no logo_url — decisión confirmada 2026-07-02 tras
    # probar ambas en producción: la URL a settings.PUBLIC_API_BASE_URL (hoy
    # https://loginmanager.casmart.internal) no carga nunca porque es un
    # dominio interno inalcanzable desde fuera. El base64 SÍ renderiza en
    # Outlook una vez que el correo se abre en ventana completa (el panel de
    # lectura no carga imágenes data: de ningún tipo hasta abrir el correo —
    # comportamiento normal de Outlook, no un bug). El logo inferior de este
    # tenant en particular sigue saliendo roto incluso en ventana completa
    # (posible problema propio de ese archivo — dimensiones/codificación —
    # no del mecanismo); pendiente que se resuba una versión más simple.
    logo_base64 = theme.logo_top_base64
    logo_bottom_base64 = theme.logo_bottom_base64

    env = _build_email_jinja2_env()
    template = env.get_template("password_reset.html.j2")
    html = template.render(
        theme=theme,
        body_html="",
        subject="",
        logo_base64=logo_base64,
        logo_url=None,
        logo_bottom_base64=logo_bottom_base64,
        logo_bottom_url=None,
        event_type="password_reset",
        cta_url=_SENTINEL_URL,
        tenant_name=tenant_name,
    )

    current_year = datetime.datetime.now().year
    subs = {
        "{{usuario_login}}": _SENTINEL_USER,
        "{{nombre_usuario}}": _SENTINEL_USER,
        "{{fecha_evento}}": _SENTINEL_NOW,
        "{{contacto_soporte}}": "soporte@casmarts.internal",
        "{{empresa_nombre}}": tenant.name,
        "{{anio}}": str(current_year),
    }
    for var, val in subs.items():
        html = html.replace(var, val)

    # Authentik no expone la IP de origen en el contexto del EmailStage —
    # se quita la fila en vez de mostrar un dato falso.
    html = re.sub(
        r"<tr>\s*<td[^>]*>IP de origen</td>\s*<td[^>]*>[^<]*</td>\s*</tr>",
        "",
        html,
    )

    # El template fuente usa {{enlace_expiracion_texto}} (para el preview y
    # el correo new_account, que sí leen password_policies.link_expiry_minutes
    # vía render_event_email_html) — pero el EmailStage real de Authentik
    # calcula su propia vigencia por token en {{ expires }}, más precisa que
    # cualquier valor fijo (nunca se desincroniza del token_expiry real).
    html = html.replace(
        "Este enlace es válido por {{enlace_expiracion_texto}} a partir del momento en que se generó.",
        "Este enlace expira {{ expires|naturaltime }}.",
    )

    html = html.replace(_SENTINEL_URL, "{{ url }}")
    html = html.replace(_SENTINEL_USER, "{{ user.name|default:user.username }}")
    html = html.replace(_SENTINEL_NOW, _DJANGO_NOW_LOCAL)

    # {{ expires|naturaltime }} necesita el tag de carga de Django, igual que
    # la plantilla original de Authentik (email/password_reset.html).
    # {% timezone %} necesita `tz` — Authentik renderiza {% now %} en UTC por
    # defecto (confirmado en producción 2026-07-02: correo mostraba 21:57
    # cuando la hora real del servidor, America/Mexico_City, era 15:57).
    html = "{% load humanize %}{% load tz %}\n" + html

    return html


def _render_email_verification_for_authentik(theme: TenantTheme, tenant: Tenant) -> str:
    """
    Igual que `_render_password_reset_for_authentik` pero para el
    EmailStage `casmarts-enrollment-verification` (registro, no
    recuperación) — mismo patrón de dos pasadas (Jinja de marca ahora,
    tags Django reales para lo que solo Authentik conoce en el envío real).
    """
    tenant_name = _strip_html_tags(theme.system_name) or theme.display_name or "CASMARTS"

    # Mismo motivo/decisión que en _render_password_reset_for_authentik:
    # base64 embebido, no logo_url (ver comentario allá para el detalle).
    logo_base64 = theme.logo_top_base64
    logo_bottom_base64 = theme.logo_bottom_base64

    env = _build_email_jinja2_env()
    template = env.get_template("email_verification.html.j2")
    html = template.render(
        theme=theme,
        body_html="",
        subject="",
        logo_base64=logo_base64,
        logo_url=None,
        logo_bottom_base64=logo_bottom_base64,
        logo_bottom_url=None,
        event_type="email_verification",
        cta_url=_SENTINEL_URL,
        tenant_name=tenant_name,
    )

    current_year = datetime.datetime.now().year
    subs = {
        "{{usuario_login}}": _SENTINEL_USER,
        "{{nombre_usuario}}": _SENTINEL_USER,
        "{{usuario_email}}": _SENTINEL_EMAIL,
        "{{fecha_evento}}": _SENTINEL_NOW,
        "{{contacto_soporte}}": "soporte@casmarts.internal",
        "{{empresa_nombre}}": tenant.name,
        "{{anio}}": str(current_year),
    }
    for var, val in subs.items():
        html = html.replace(var, val)

    # El texto de preview decía "24 horas" fijo — el EmailStage real usa su
    # propio token_expiry (hoy 30 min, ver casmarts-email-verification.yaml),
    # así que se reemplaza por el valor dinámico real de cada envío.
    html = html.replace(
        "Este enlace expirará en 24 horas.",
        "Este enlace expira {{ expires|naturaltime }}.",
    )

    html = html.replace(_SENTINEL_URL, "{{ url }}")
    html = html.replace(_SENTINEL_USER, "{{ user.name|default:user.username }}")
    html = html.replace(_SENTINEL_EMAIL, "{{ user.email }}")
    html = html.replace(_SENTINEL_NOW, _DJANGO_NOW_LOCAL)

    html = "{% load humanize %}{% load tz %}\n" + html

    return html


_RENDERERS = {
    "password_reset": _render_password_reset_for_authentik,
    "email_verification": _render_email_verification_for_authentik,
}


@email_sync_router.post("/deploy-to-authentik/{event_type}")
async def deploy_email_to_authentik(
    event_type: str,
    flow_slug: str = Query("default-authentication-flow"),
    db: AsyncSession = Depends(get_db),
):
    """
    Despliega la plantilla real de Authentik para `event_type` (los tipos
    con EmailStage nativo, ver _AUTHENTIK_EMAIL_STAGES) usando el tema
    GLOBAL del flow (sin app_slug) — Authentik no puede diferenciar por
    tenant, solo hay un Brand/EmailStage compartido en esta instancia.
    """
    stage_info = _AUTHENTIK_EMAIL_STAGES.get(event_type)
    if not stage_info:
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{event_type}' no tiene un EmailStage real en Authentik. "
                f"Tipos desplegables así: {', '.join(_AUTHENTIK_EMAIL_STAGES)}; "
                "los demás eventos se envían vía el puente de eventos/webhook."
            ),
        )
    authentik_stage_name, authentik_template_rel_path = stage_info

    if not settings.AUTHENTIK_API_TOKEN or not settings.AUTHENTIK_HOST:
        raise HTTPException(
            status_code=503,
            detail="AUTHENTIK_API_TOKEN/AUTHENTIK_HOST no configurados en .env.",
        )

    result = await db.execute(
        select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None),
        )
    )
    theme = result.scalar_one_or_none()
    if not theme:
        raise HTTPException(status_code=404, detail=f"No hay tema global para flow '{flow_slug}'.")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == theme.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado para este tema.")

    html = _RENDERERS[event_type](theme, tenant)

    output_dir = Path("/shared/authentik/templates/email")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / Path(authentik_template_rel_path).name
        output_path.write_text(html, encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo escribir en el volumen compartido: {str(e)}.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bearer {settings.AUTHENTIK_API_TOKEN}"}
            list_resp = await client.get(f"{settings.AUTHENTIK_HOST}/api/v3/stages/email/", headers=headers)
            list_resp.raise_for_status()
            stage = next(
                (s for s in list_resp.json().get("results", []) if s.get("name") == authentik_stage_name),
                None,
            )
            if not stage:
                raise HTTPException(
                    status_code=502,
                    detail=f"No se encontró el EmailStage '{authentik_stage_name}' en Authentik.",
                )
            patch_resp = await client.patch(
                f"{settings.AUTHENTIK_HOST}/api/v3/stages/email/{stage['pk']}/",
                headers=headers,
                json={"template": authentik_template_rel_path},
            )
            patch_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error de la API de Authentik: {e.response.text[:300]}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=504, detail=f"No se pudo contactar a Authentik: {str(e)}")

    log.info("Plantilla de Authentik desplegada: %s -> %s", event_type, authentik_template_rel_path)
    return {
        "status": "deployed",
        "event_type": event_type,
        "path": str(output_path),
        "authentik_stage": authentik_stage_name,
        "authentik_template": authentik_template_rel_path,
    }
