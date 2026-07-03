import logging
import re
import secrets
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.cache import cache
from app.config import settings
from app.database import get_db
from app.models.email_body import TenantEmailBody
from app.models.tenant import Tenant
from app.models.tenant_theme import TenantTheme
from app.routers.admin import (
    _b64_to_bytes,
    _send_smtp,
    _strip_html_tags,
    authentik_engine,
    render_event_email_html,
)

log = logging.getLogger(__name__)

authentik_events_router = APIRouter(prefix="/api/v1/webhooks", tags=["Authentik Events"])

# Mapea el `action` (EventAction de Authentik) al event_type de Vista Correo.
# - password_set: piloto original.
# - user_write: Authentik lo dispara también en ediciones de perfil, no
#   solo altas — el filtro por context.created ya ocurre en Authentik
#   (casmarts-new-account-matcher, ver casmarts-event-webhooks.yaml), así
#   que todo lo que llega aquí con esta action ya es una alta real.
# - login_failed: NO implica bloqueo por sí solo — ver
#   _is_account_locked_out() más abajo, que reevalúa el score real antes
#   de decidir si se manda el correo.
EVENT_ACTION_TO_EMAIL_TYPE = {
    "password_set": "security_change",
    "user_write": "new_account",
    "login_failed": "account_lockout",
}

# Umbral real configurado en casmarts-lockout-reputation (Authentik) — debe
# coincidir exactamente, si no la ventana de "está bloqueado de verdad" que
# calculamos aquí queda desincronizada de la que aplica Authentik.
_LOCKOUT_REPUTATION_THRESHOLD = -5
# Evita reenviar el correo de bloqueo en cada intento fallido repetido
# mientras la cuenta ya está bloqueada.
_LOCKOUT_NOTIFY_COOLDOWN_SECONDS = 3600

# app_slugs con grupo de Authentik dedicado (ver Parte 1.5 / casmarts-app-enrollment.yaml).
KNOWN_APP_SLUGS = {"starter", "consulta-smart", "idp-smart", "centinela-ai", "kiwi", "plane"}

_FLOW_SLUG = "default-authentication-flow"

_CTA_FLOW_MAP = {
    "password_reset": "password-recovery",
    "email_verification": "default-source-enrollment",
    "new_account": "password-recovery",
    "account_lockout": "default-authentication-flow",
    "security_change": "default-user-settings-flow",
}


def _verify_webhook_secret(x_webhook_secret: str | None = Header(default=None)):
    """Secreto de un solo propósito para el webhook — separado de
    ADMIN_API_KEY para que un compromiso de uno no dé acceso al otro."""
    if not settings.AUTHENTIK_WEBHOOK_SECRET or not x_webhook_secret or not secrets.compare_digest(
        x_webhook_secret, settings.AUTHENTIK_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=401, detail="Webhook secret inválido o ausente.")


async def _resolve_app_slug(user_username: str) -> str | None:
    """Resuelve a qué aplicación pertenece el usuario vía sus grupos reales
    de Authentik (Parte 1.5) — el evento en sí no trae ese dato (confirmado
    vacío para password_set). Sin grupo de app reconocido, devuelve None
    (el llamador cae al tema global, mismo comportamiento que password_reset)."""
    if not settings.AUTHENTIK_API_TOKEN or not settings.AUTHENTIK_HOST:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.AUTHENTIK_HOST}/api/v3/core/users/",
                headers={"Authorization": f"Bearer {settings.AUTHENTIK_API_TOKEN}"},
                params={"username": user_username},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                return None
            # Comparación case-insensitive: el grupo "Starter" (preexistente,
            # capitalizado) debe resolver al app_slug 'starter' (minúsculas,
            # como está en TenantTheme.authentik_app_slug).
            group_names_lower = {g["name"].lower() for g in results[0].get("groups_obj", [])}
            matched = sorted(group_names_lower & KNOWN_APP_SLUGS)
            return matched[0] if matched else None
    except httpx.HTTPError as e:
        log.warning("No se pudo resolver grupos de Authentik para '%s': %s", user_username, e)
        return None


async def _is_account_locked_out(username: str) -> bool:
    """
    Reevalúa si `username` está REALMENTE bloqueado ahora mismo, en vez de
    confiar en que "hubo un login_failed" ya implica bloqueo (no es así —
    la mayoría de los login_failed son solo un typo).

    Replica la agregación exacta de ReputationPolicy.passes() (confirmado
    leyendo authentik/policies/reputation/models.py en la instancia real):
    con check_ip=False y check_username=True, el score real es la SUMA de
    todas las filas de Reputation para ese identifier (no la última fila),
    y el umbral debe coincidir con casmarts-lockout-reputation en Authentik.
    """
    async with authentik_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COALESCE(SUM(score), 0) AS total_score "
                "FROM authentik_policies_reputation_reputation "
                "WHERE identifier = :username"
            ),
            {"username": username},
        )
        total_score = result.scalar_one()
    return total_score <= _LOCKOUT_REPUTATION_THRESHOLD


@authentik_events_router.post("/authentik-event", dependencies=[Depends(_verify_webhook_secret)])
async def handle_authentik_event(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recibe eventos reales de Authentik (NotificationTransport modo webhook,
    ver core-casmarts/casmarts-app-enrollment.yaml — o el blueprint de
    notificaciones correspondiente) y envía el correo real diseñado en Vista
    Correo, usando datos reales del usuario (no placeholders de preview).
    """
    payload = await request.json()
    action = payload.get("action")
    event_type = EVENT_ACTION_TO_EMAIL_TYPE.get(action)
    if not event_type:
        log.info("Webhook de Authentik ignorado (action=%s sin mapeo a correo)", action)
        return {"status": "ignored", "reason": f"acción '{action}' sin mapeo a correo"}

    event_uuid = payload.get("event_uuid")
    user_username = payload.get("user_username")
    user_email = payload.get("user_email")
    if not user_username or not user_email:
        raise HTTPException(status_code=422, detail="Payload incompleto: falta user_username/user_email.")

    if event_uuid:
        dedup_key = f"authentik_webhook_processed:{event_uuid}"
        if await cache.get(dedup_key):
            log.info("Webhook de Authentik duplicado (event_uuid=%s), ignorado.", event_uuid)
            return {"status": "duplicate", "event_uuid": event_uuid}
        await cache.set(dedup_key, "1", ex=86400)

    if event_type == "account_lockout":
        # La mayoría de los login_failed son solo un typo, no un bloqueo —
        # solo mandamos el correo si el score real ya cruzó el umbral que
        # aplica casmarts-lockout-reputation en Authentik.
        if not await _is_account_locked_out(user_username):
            return {"status": "ignored", "reason": "score de reputación por encima del umbral de bloqueo"}
        cooldown_key = f"account_lockout_notified:{user_username}"
        if await cache.get(cooldown_key):
            return {"status": "ignored", "reason": "correo de bloqueo ya enviado recientemente (cooldown)"}
        await cache.set(cooldown_key, "1", ex=_LOCKOUT_NOTIFY_COOLDOWN_SECONDS)

    app_slug = await _resolve_app_slug(user_username)

    theme = None
    if app_slug:
        r = await db.execute(select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == _FLOW_SLUG,
            TenantTheme.authentik_app_slug == app_slug,
        ))
        theme = r.scalar_one_or_none()
    if theme is None:
        r = await db.execute(select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == _FLOW_SLUG,
            TenantTheme.authentik_app_slug.is_(None),
        ))
        theme = r.scalar_one_or_none()
    if not theme:
        raise HTTPException(status_code=404, detail=f"No hay tema configurado para flow '{_FLOW_SLUG}'.")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == theme.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado para este tema.")

    eb = await db.execute(select(TenantEmailBody).where(
        TenantEmailBody.tenant_id == tenant.id,
        TenantEmailBody.flow_slug == _FLOW_SLUG,
        TenantEmailBody.event_type == event_type,
    ))
    email_body = eb.scalar_one_or_none()
    db_body_html = email_body.body_html if email_body else ''
    db_subject = email_body.subject if email_body else ''

    tenant_name = _strip_html_tags(theme.system_name) or theme.display_name or 'CASMARTS'

    app_qs = f'?app={app_slug}' if app_slug else ''
    logo_bytes, logo_mime = b'', 'image/png'
    logo_base64 = None
    logo_url = None
    if theme.logo_top_base64:
        logo_bytes, logo_mime = _b64_to_bytes(theme.logo_top_base64)
        logo_base64 = theme.logo_top_base64
        if len(logo_bytes) > 200 * 1024:
            log.warning("Logo superior >200 KB para flow '%s' — omitido.", _FLOW_SLUG)
            logo_bytes = b''
            logo_base64 = None
        else:
            logo_url = f'{settings.PUBLIC_API_BASE_URL}/api/v1/public/theme/{_FLOW_SLUG}/image/logo_top{app_qs}'

    logo_bottom_bytes, logo_bottom_mime = b'', 'image/png'
    logo_bottom_base64 = None
    logo_bottom_url = None
    if theme.logo_bottom_base64:
        if len(theme.logo_bottom_base64.encode()) > 200 * 1024:
            log.warning("Logo inferior >200 KB para flow '%s' — omitido.", _FLOW_SLUG)
        else:
            logo_bottom_bytes, logo_bottom_mime = _b64_to_bytes(theme.logo_bottom_base64)
            logo_bottom_base64 = theme.logo_bottom_base64
            logo_bottom_url = f'{settings.PUBLIC_API_BASE_URL}/api/v1/public/theme/{_FLOW_SLUG}/image/logo_bottom{app_qs}'

    cta_url = f"https://auth.casmart.internal/if/flow/{_CTA_FLOW_MAP.get(event_type, 'default-authentication-flow')}/"
    user_name_full = user_username.split('@')[0].replace('.', ' ').title()

    html = render_event_email_html(
        theme=theme,
        tenant=tenant,
        event_type=event_type,
        body_html=db_body_html,
        subject=db_subject,
        logo_base64=logo_base64,
        logo_url=logo_url,
        logo_bottom_base64=logo_bottom_base64,
        logo_bottom_url=logo_bottom_url,
        cta_url=cta_url,
        tenant_name=tenant_name,
        substitution_values={
            'usuario_login': user_username,
            'usuario_email': user_email,
            'nombre_usuario': user_name_full,
            'realizado_por': f'Usuario: {user_name_full}',
            'aplicacion_nombre': (app_slug or 'default').replace('-', ' ').title(),
            'aplicacion_slug': app_slug or 'default',
            'fecha_evento': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'fecha_hora_cambio': datetime.now().isoformat(),
        },
    )

    subject_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    subject_text = subject_match.group(1).strip() if subject_match else 'Notificación'

    try:
        _send_smtp(user_email, subject_text, html, logo_bytes, logo_mime, logo_bottom_bytes, logo_bottom_mime)
    except Exception as e:
        log.error("Error enviando correo real (evento Authentik): %s", e)
        raise HTTPException(status_code=502, detail=f"Error SMTP: {str(e)}")

    log.info("Correo real enviado: event=%s user=%s app_slug=%s", event_type, user_username, app_slug)
    return {"status": "sent", "event_type": event_type, "to": user_email, "app_slug": app_slug}
