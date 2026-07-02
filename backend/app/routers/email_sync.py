import logging
import os
import httpx
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.email_body import TenantEmailBody, EMAIL_EVENT_TYPES
from app.routers.admin import verify_admin_key

log = logging.getLogger(__name__)

email_sync_router = APIRouter(
    prefix="/api/v1/emails",
    tags=["Email Sync"],
    dependencies=[Depends(verify_admin_key)],
)

AUTHENTIK_TEMPLATE_MAP = {
    "password_reset": "authentik_core-password-reset",
    "email_verification": "authentik_core-email-confirmation",
    "new_account": "authentik_core-user-created",
    "account_lockout": "authentik_core-account-locked",
    "security_change": "authentik_core-security-alert"
}


@email_sync_router.get("/export/{event_type}")
async def export_email_template(
    event_type: str,
    tenant_id: str = Query("00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta plantilla de email para sincronizar a Authentik

    Query params:
    - event_type: password_reset, email_verification, new_account, account_lockout, security_change
    - tenant_id: UUID del tenant (default: CASMARTS)

    Ejemplo: GET /api/v1/emails/export/password_reset

    Response:
    {
        "event_type": "password_reset",
        "subject": "Restablecer contraseña",
        "body_html": "<html>...",
        "authentik_template_name": "authentik_core-password-reset",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "status": "ready_to_sync"
    }
    """

    if event_type not in EMAIL_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {sorted(EMAIL_EVENT_TYPES)}"
        )

    result = await db.execute(
        select(TenantEmailBody).where(
            TenantEmailBody.tenant_id == tenant_id,
            TenantEmailBody.event_type == event_type
        )
    )
    email_body = result.scalar_one_or_none()

    if not email_body:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found for event_type={event_type}, tenant_id={tenant_id}"
        )

    return {
        "event_type": event_type,
        "subject": email_body.subject,
        "body_html": email_body.body_html,
        "authentik_template_name": AUTHENTIK_TEMPLATE_MAP.get(event_type),
        "tenant_id": tenant_id,
        "status": "ready_to_sync"
    }


@email_sync_router.post("/sync-to-authentik")
async def sync_to_authentik(
    event_type: str = Query(...),
    tenant_id: str = Query("00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db)
):
    """
    Sincroniza plantilla de Login Manager a Authentik vía API

    Requiere: AUTHENTIK_HOST y AUTHENTIK_API_TOKEN en variables de entorno

    Ejemplo: POST /api/v1/emails/sync-to-authentik?event_type=password_reset

    Returns:
    {
        "status": "synced",
        "event_type": "password_reset",
        "authentik_template": "authentik_core-password-reset"
    }
    """

    if event_type not in EMAIL_EVENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid event_type: {event_type}")

    authentik_host = os.getenv("AUTHENTIK_HOST", "http://auth.casmart.internal")
    authentik_token = os.getenv("AUTHENTIK_API_TOKEN")

    if not authentik_token:
        log.warning("AUTHENTIK_API_TOKEN not configured. Manual sync guide should be used.")
        raise HTTPException(
            status_code=503,
            detail="AUTHENTIK_API_TOKEN not configured. Use manual sync guide instead."
        )

    # Obtener template de Login Manager
    result = await db.execute(
        select(TenantEmailBody).where(
            TenantEmailBody.tenant_id == tenant_id,
            TenantEmailBody.event_type == event_type
        )
    )
    email_body = result.scalar_one_or_none()

    if not email_body:
        raise HTTPException(status_code=404, detail=f"Template not found for {event_type}")

    template_name = AUTHENTIK_TEMPLATE_MAP.get(event_type)

    # Llamar API de Authentik para actualizar template
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{authentik_host}/api/v3/core/email_templates/{template_name}/",
                headers={
                    "Authorization": f"Bearer {authentik_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "subject": email_body.subject,
                    "html": email_body.body_html
                }
            )

            if response.status_code == 200:
                log.info(f"✅ Email template synced: {event_type} → {template_name}")
                return {
                    "status": "synced",
                    "event_type": event_type,
                    "authentik_template": template_name,
                    "tenant_id": tenant_id
                }
            else:
                error_msg = response.text[:200] if response.text else response.status_code
                log.error(f"❌ Authentik API error: {error_msg}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Authentik API error: {error_msg}"
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Authentik API timeout. Check if {authentik_host} is reachable."
        )
    except Exception as e:
        log.error(f"Sync failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )
