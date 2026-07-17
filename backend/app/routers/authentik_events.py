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
    _format_link_expiry_text,
    _get_link_expiry_minutes,
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
    "login": "login_success",
    "suspicious_request": "suspicious_request",
    "invitation_used": "invitation_used",
    "authorize_application": "app_authorized",
}

# Evita reenviar el correo de bloqueo en cada intento fallido repetido
# mientras la cuenta ya está bloqueada.
_LOCKOUT_NOTIFY_COOLDOWN_SECONDS = 3600

# Control anti-spam para eventos de alto volumen.
# - login_success: no más de 1 correo por usuario cada 24h.
# - app_authorized: no más de 1 correo por usuario+app cada 30 días.
_EVENT_NOTIFY_COOLDOWN_SECONDS: dict[str, int] = {
    "login_success": 24 * 60 * 60,
    "app_authorized": 30 * 24 * 60 * 60,
}

# app_slugs con grupo de Authentik dedicado (ver Parte 1.5 / casmarts-app-enrollment.yaml).
KNOWN_APP_SLUGS = {"starter", "consulta-smart", "idp-smart", "centinela-ai", "kiwi", "plane"}

_FLOW_SLUG = "default-authentication-flow"

_CTA_FLOW_MAP = {
    "password_reset": "password-recovery",
    "email_verification": "default-source-enrollment",
    "new_account": "password-recovery",
    "account_lockout": "default-authentication-flow",
    "security_change": "default-user-settings-flow",
    "account_locked_admin": "default-authentication-flow",
    "account_unlocked_admin": "default-authentication-flow",
    "login_success": "default-authentication-flow",
    "suspicious_request": "default-authentication-flow",
    "invitation_used": "default-authentication-flow",
    "app_authorized": "default-authentication-flow",
    "impersonation_started": "default-user-settings-flow",
    "account_deleted": "default-authentication-flow",
}


def _verify_webhook_secret(x_webhook_secret: str | None = Header(default=None)):
    """Secreto de un solo propósito para el webhook — separado de
    ADMIN_API_KEY para que un compromiso de uno no dé acceso al otro."""
    if not settings.AUTHENTIK_WEBHOOK_SECRET or not x_webhook_secret or not secrets.compare_digest(
        x_webhook_secret, settings.AUTHENTIK_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=401, detail="Webhook secret inválido o ausente.")


async def _resolve_app_slug_from_client_id(oauth_client_id: str | None) -> str | None:
    """Resuelve el app_slug EXACTO a partir del client_id OAuth2 del
    authorize pendiente que quedó registrado en el evento (ver
    casmarts-webhook-body-mapping en casmarts-event-webhooks.yaml —
    event.context.http_request.args.client_id). Esto solo existe cuando el
    usuario llegó al password_set/user_write vía el enlace de recuperación
    de una app específica; deterministic — a diferencia de adivinar por
    grupos, no puede confundir apps distintas de un usuario multi-app
    (confirmado en vivo 2026-07-04: Lmitchell, solo en el grupo
    'centinela-ai', cambió su password desde Starter — el heurístico de
    grupos mandó el correo con branding de Centinela AI en vez de Starter)."""
    if not oauth_client_id or not settings.AUTHENTIK_API_TOKEN or not settings.AUTHENTIK_HOST:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.AUTHENTIK_HOST}/api/v3/providers/oauth2/",
                headers={"Authorization": f"Bearer {settings.AUTHENTIK_API_TOKEN}"},
                params={"client_id": oauth_client_id},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                return None
            slug = results[0].get("assigned_application_slug")
            return slug.lower() if slug else None
    except httpx.HTTPError as e:
        log.warning("No se pudo resolver la app de Authentik para client_id '%s': %s", oauth_client_id, e)
        return None


async def _resolve_app_from_pk(app_pk: str) -> tuple[str | None, str | None]:
    """Resuelve (slug, nombre) de una Application real por su pk — usado por
    app_authorized, donde event.context.authorized_application ya trae la
    referencia exacta a la app (sin ambigüedad de client_id/grupos).

    Vía SQL directo, no la API REST: /api/v3/core/applications/{lookup}/
    resuelve por SLUG, no por pk (confirmado en vivo 2026-07-04 — un GET con
    el pk real de la app dio 404, y ni ?pk= ni ?policybindingmodel_ptr_id=
    filtran el listado). model_to_dict() en Authentik solo da el pk crudo,
    así que se consulta authentik_core_application directo, igual que
    _is_account_locked_out consulta authentik_policies_reputation_reputation."""
    if not app_pk:
        return None, None
    try:
        async with authentik_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT slug, name FROM authentik_core_application WHERE policybindingmodel_ptr_id = :pk"),
                {"pk": app_pk},
            )
            row = result.first()
    except Exception as e:
        log.warning("No se pudo resolver la app de Authentik para pk='%s': %s", app_pk, e)
        return None, None
    if not row:
        return None, None
    return (row[0] or "").lower() or None, row[1]


async def _resolve_app_slug_from_groups(user_username: str) -> str | None:
    """Fallback: resuelve a qué aplicación pertenece el usuario vía sus
    grupos reales de Authentik (Parte 1.5) — usado solo cuando el evento no
    trae oauth_client_id (p. ej. un admin cambiando la password de alguien
    directo desde /core/users/{id}/set_password/, sin flujo OAuth de por
    medio). Es un best-effort ambiguo: si el usuario pertenece a más de un
    grupo de app reconocido, puede resolver a la app equivocada — ver
    _resolve_app_slug_from_client_id para el caso exacto."""
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
            # Con MÁS de un grupo de app reconocido no hay forma de saber cuál
            # de los dos disparó este evento en particular — devolver el
            # primero alfabéticamente adivinaba mal con usuarios multi-app
            # (confirmado en vivo 2026-07-04: Lmitchell en 'casmarts' +
            # 'centinela-ai' recibió el correo de Centinela AI aunque el
            # cambio fue desde Starter). Mejor caer al tema global/genérico
            # que mandar branding de una app equivocada con confianza.
            if len(matched) != 1:
                return None
            return matched[0]
    except httpx.HTTPError as e:
        log.warning("No se pudo resolver grupos de Authentik para '%s': %s", user_username, e)
        return None


async def _resolve_app_slug(user_username: str, oauth_client_id: str | None, http_path: str | None = None) -> str | None:
    slug = await _resolve_app_slug_from_client_id(oauth_client_id)
    if slug:
        return slug

    # CAMBIO 2026-07-09: ANTES resolvía cualquier app si su nombre aparecía
    # en el http_path, incluyendo query params (ambiguo + frágil cuando hay
    # múltiples apps en la URL). AHORA solo resuelve si el PATH (sin ?) contiene
    # la app explícitamente, p. ej. /password-reset-centinela/ (no implementado
    # en nuestro flujo) — rechaza query-param-based resolution para evitar
    # hijack por sesiones anteriores / enlaces con ?app=X. Sin esto, un usuario
    # multi-app que hace password reset mientras tenía ?app=centinela en otra
    # pestaña podría recibir branding de Centinela aunque el reset fuera desde
    # Starter (confirmado en vivo 2026-07-09).
    # Fallback: http_path se ignora, vuelve a _resolve_app_slug_from_groups.

    return await _resolve_app_slug_from_groups(user_username)


async def _get_lockout_threshold(db: AsyncSession) -> int:
    """Umbral real configurado en casmarts-lockout-reputation (Authentik),
    espejo de PasswordPolicy.lockout_failed_attempts — debe coincidir
    exactamente, si no la ventana de "está bloqueado de verdad" que
    calculamos aquí queda desincronizada de la que aplica Authentik (ver
    _push_to_authentik en password_policy.py, que sincroniza el valor real)."""
    from app.models.password_policy import PasswordPolicy, SINGLETON_ID
    result = await db.execute(select(PasswordPolicy).where(PasswordPolicy.id == SINGLETON_ID))
    policy = result.scalar_one_or_none()
    attempts = policy.lockout_failed_attempts if policy else 5
    return -attempts


async def _is_account_locked_out(username: str, db: AsyncSession) -> bool:
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
    threshold = await _get_lockout_threshold(db)
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
    return total_score <= threshold


_USER_SNAPSHOT_CACHE_PREFIX = "user_snapshot"
_USER_SNAPSHOT_TTL_SECONDS = 315360000


async def _snapshot_user(pk: str, username: str, email: str) -> None:
    await cache.set(f"{_USER_SNAPSHOT_CACHE_PREFIX}:{pk}", f"{username}\n{email}", ex=_USER_SNAPSHOT_TTL_SECONDS)


async def _resolve_account_deleted_event(payload: dict) -> tuple[str, str] | None:
    """model_deleted en un User real — el registro ya no existe para
    volver a consultarlo vía API (a diferencia de model_updated), así que
    depende del snapshot username/email guardado por _snapshot_user en el
    último model_updated visto de ese pk. Sin snapshot previo, no hay a
    quién mandarle el correo — se ignora (no hay dirección real conocida)."""
    if payload.get("model_app") != "authentik_core" or payload.get("model_name") != "user":
        return None
    model_pk = payload.get("model_pk")
    if not model_pk:
        return None
    snapshot = await cache.get(f"{_USER_SNAPSHOT_CACHE_PREFIX}:{model_pk}")
    if not snapshot:
        return None
    username, _, email = snapshot.partition("\n")
    if not email:
        return None
    return username, email


_USER_ACTIVE_STATE_CACHE_PREFIX = "user_active_state"
# Esto es un tracker de estado persistente, no un cache de corta duración —
# cache.set() por defecto expira a los 300s, lo que borraría el último
# is_active visto y haría que CUALQUIER save posterior (p. ej. el próximo
# login, que actualiza last_login) se tratara como "primera vez" y se
# reseteara en silencio, perdiendo bloqueos/desbloqueos reales ocurridos
# mientras tanto. ~10 años en segundos, efectivamente indefinido.
_USER_ACTIVE_STATE_TTL_SECONDS = 315360000


async def _resolve_admin_toggle_event(payload: dict) -> tuple[str, str, str, str] | None:
    """
    model_updated no distingue QUÉ campo cambió (model_to_dict solo da
    {app, model_name, pk, name} — ver authentik/events/utils.py), así que se
    vuelve a consultar el usuario por su pk vía la API REST para conocer su
    is_active REAL ahora mismo, y se compara contra el último valor visto
    (Valkey, sin expiración — es un estado, no un evento puntual).

    Devuelve (event_type, username_real, email_real, actor_username) solo si
    hubo una transición real de is_active, o None si hay que ignorar este
    evento (primera vez que se ve este usuario, sin cambio real, o payload
    incompleto). `username_real`/`email_real` son del usuario AFECTADO (via
    pk) — payload["user_username"/"user_email"] en este action es del ACTOR
    (quien hizo la request), útil solo como `actor_username` para
    {{realizado_por}}.
    """
    if payload.get("model_app") != "authentik_core" or payload.get("model_name") != "user":
        return None
    model_pk = payload.get("model_pk")
    if not model_pk:
        return None
    if not settings.AUTHENTIK_API_TOKEN or not settings.AUTHENTIK_HOST:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.AUTHENTIK_HOST}/api/v3/core/users/{model_pk}/",
                headers={"Authorization": f"Bearer {settings.AUTHENTIK_API_TOKEN}"},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            user_obj = resp.json()
    except httpx.HTTPError as e:
        log.warning("No se pudo consultar el usuario pk=%s para detectar bloqueo/desbloqueo: %s", model_pk, e)
        return None

    current_active = bool(user_obj.get("is_active"))
    cache_key = f"{_USER_ACTIVE_STATE_CACHE_PREFIX}:{model_pk}"
    previous_raw = await cache.get(cache_key)

    await cache.set(cache_key, "1" if current_active else "0", ex=_USER_ACTIVE_STATE_TTL_SECONDS)
    # Snapshot de username/email por pk — el registro deja de existir tras un
    # model_deleted real, así que account_deleted (más abajo) no puede volver
    # a consultarlo vía API; se apoya en este snapshot, mantenido fresco en
    # cada model_updated que vemos de un User.
    await _snapshot_user(model_pk, user_obj.get("username", ""), user_obj.get("email", ""))

    if previous_raw is None:
        # Primera vez que vemos a este usuario — se fija el estado base sin
        # avisar (si no, cualquier usuario ya inactivo antes de desplegar
        # esta función dispararía un falso "bloqueo por admin" en su próximo
        # save, y toda alta nueva ya la cubre new_account por separado).
        return None

    previous_active = previous_raw == "1"
    if previous_active == current_active:
        return None  # mismo save de siempre (p. ej. last_login) — sin transición real

    event_type = "account_unlocked_admin" if current_active else "account_locked_admin"
    actor_username = payload.get("user_username") or "un administrador"
    return event_type, user_obj.get("username", ""), user_obj.get("email", ""), actor_username


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
    oauth_client_id = payload.get("oauth_client_id")
    authorized_app_pk = payload.get("authorized_app_pk")
    actor_username: str | None = None

    # Requisito operativo: no enviar más correos por inicio de sesión exitoso.
    if action == "login":
        return {"status": "ignored", "reason": "login_success deshabilitado"}

    if action == "model_updated":
        resolved = await _resolve_admin_toggle_event(payload)
        if resolved is None:
            log.info("Webhook de Authentik ignorado (model_updated sin transición real de is_active)")
            return {"status": "ignored", "reason": "sin transición real de is_active"}
        event_type, user_username, user_email, actor_username = resolved
    elif action == "model_deleted":
        resolved_del = await _resolve_account_deleted_event(payload)
        if resolved_del is None:
            log.info("Webhook de Authentik ignorado (model_deleted sin snapshot conocido o no es un User)")
            return {"status": "ignored", "reason": "sin snapshot conocido para este pk, o no es un User"}
        event_type = "account_deleted"
        user_username, user_email = resolved_del
    elif action == "impersonation_started":
        # event.user es el ADMIN (no la persona impersonada) — ver
        # casmarts-impersonation-started-matcher en el blueprint. El
        # objetivo real está en on_behalf_of_username/email.
        event_type = "impersonation_started"
        user_username = payload.get("on_behalf_of_username")
        user_email = payload.get("on_behalf_of_email")
        actor_username = payload.get("user_username")
        if not user_username or not user_email:
            log.warning("impersonation_started sin on_behalf_of — evento descartado (payload incompleto)")
            return {"status": "ignored", "reason": "sin on_behalf_of en el evento"}
    else:
        event_type = EVENT_ACTION_TO_EMAIL_TYPE.get(action)
        if not event_type:
            log.info("Webhook de Authentik ignorado (action=%s sin mapeo a correo)", action)
            return {"status": "ignored", "reason": f"acción '{action}' sin mapeo a correo"}
        user_username = payload.get("user_username")
        user_email = payload.get("user_email")

    event_uuid = payload.get("event_uuid")
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
        if not await _is_account_locked_out(user_username, db):
            return {"status": "ignored", "reason": "score de reputación por encima del umbral de bloqueo"}
        cooldown_key = f"account_lockout_notified:{user_username}"
        if await cache.get(cooldown_key):
            return {"status": "ignored", "reason": "correo de bloqueo ya enviado recientemente (cooldown)"}
        await cache.set(cooldown_key, "1", ex=_LOCKOUT_NOTIFY_COOLDOWN_SECONDS)

    authorized_app_name: str | None = None
    if event_type == "app_authorized" and authorized_app_pk:
        # authorized_app_pk viene directo de event.context.authorized_application
        # (la Application real que se autorizó) — más confiable que cualquier
        # heurística de client_id/grupos, se usa tal cual para el tema Y para
        # {{aplicacion_nombre}}.
        app_slug, authorized_app_name = await _resolve_app_from_pk(authorized_app_pk)
    else:
        app_slug = await _resolve_app_slug(user_username, oauth_client_id, payload.get("http_path"))

    # DEBUG: Log full resolution chain para diagnosticar email branding equivocado
    log.warning(
        "email_app_resolution: user=%s event=%s oauth_client_id=%s http_path=%s → app_slug=%s",
        user_username, event_type, oauth_client_id, payload.get("http_path"), app_slug
    )

    # Cooldown por tipo de evento para evitar correos repetitivos ante
    # reautenticaciones/consentimientos frecuentes del mismo usuario.
    event_cooldown = _EVENT_NOTIFY_COOLDOWN_SECONDS.get(event_type)
    if event_cooldown:
        app_scope = app_slug or (authorized_app_pk or oauth_client_id or "global")
        cooldown_key = f"event_notify_cooldown:{event_type}:{user_username.lower()}:{app_scope}"
        if await cache.get(cooldown_key):
            return {
                "status": "ignored",
                "reason": f"correo '{event_type}' ya enviado recientemente (cooldown)",
            }
        await cache.set(cooldown_key, "1", ex=event_cooldown)

    theme = None
    theme_source = None
    if app_slug:
        r = await db.execute(select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == _FLOW_SLUG,
            TenantTheme.authentik_app_slug == app_slug,
        ))
        theme = r.scalar_one_or_none()
        if theme:
            theme_source = f"app-specific ({app_slug})"
    if theme is None:
        r = await db.execute(select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == _FLOW_SLUG,
            TenantTheme.authentik_app_slug.is_(None),
        ))
        theme = r.scalar_one_or_none()
        if theme:
            theme_source = "global"
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
    # Preferir el nombre real (User.name, vía casmarts-webhook-body-mapping) —
    # el username no siempre tiene forma "nombre.apellido" (p.ej. "lmitchell"),
    # así que adivinarlo a partir de ahí producía saludos como "Hola Lmitchell"
    # en vez de "Hola Luis Mitchell" (confirmado en vivo 2026-07-07). Se
    # conserva el heurístico viejo solo como respaldo para payloads sin
    # user_name (p.ej. account_deleted, que depende de un snapshot antiguo).
    user_name_full = payload.get("user_name") or user_username.split('@')[0].replace('.', ' ').title()

    link_expiry_minutes = await _get_link_expiry_minutes(db)

    # account_locked_admin/account_unlocked_admin: quien "realizó" la acción
    # es el admin que hizo el toggle (actor_username), no el propio usuario
    # afectado — para el resto de eventos (self-service) sigue siendo el
    # mismo usuario.
    realizado_por = f'Administrador: {actor_username}' if actor_username else f'Usuario: {user_name_full}'

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
            'realizado_por': realizado_por,
            'aplicacion_nombre': authorized_app_name or (app_slug or 'default').replace('-', ' ').title(),
            'aplicacion_slug': app_slug or 'default',
            'fecha_evento': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'fecha_hora_cambio': datetime.now().isoformat(),
            'enlace_expiracion_texto': _format_link_expiry_text(link_expiry_minutes),
        },
    )

    subject_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    subject_text = subject_match.group(1).strip() if subject_match else 'Notificación'

    try:
        _send_smtp(user_email, subject_text, html, logo_bytes, logo_mime, logo_bottom_bytes, logo_bottom_mime)
    except Exception as e:
        log.error("Error enviando correo real (evento Authentik): %s", e)
        raise HTTPException(status_code=502, detail=f"Error SMTP: {str(e)}")

    log.info(
        "Correo real enviado: event=%s user=%s app_slug=%s theme_source=%s logo=%s",
        event_type, user_username, app_slug, theme_source, "top_present" if theme.logo_top_base64 else "none"
    )
    return {"status": "sent", "event_type": event_type, "to": user_email, "app_slug": app_slug, "theme_source": theme_source}
