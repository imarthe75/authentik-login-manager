#!/usr/bin/env python3
"""
Script para sincronizar plantillas de email de Login Manager a Authentik

Uso:
    export AUTHENTIK_API_TOKEN="<token>"
    python scripts/sync_emails_to_authentik.py

Variables de entorno requeridas:
    AUTHENTIK_HOST: URL de Authentik (default: http://auth.casmart.internal)
    AUTHENTIK_API_TOKEN: Bearer token de Authentik
"""

import asyncio
import httpx
import os
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine
from app.models.email_body import TenantEmailBody, EMAIL_EVENT_TYPES
from sqlalchemy.future import select

AUTHENTIK_TEMPLATE_MAP = {
    "password_reset": "authentik_core-password-reset",
    "email_verification": "authentik_core-email-confirmation",
    "new_account": "authentik_core-user-created",
    "account_lockout": "authentik_core-account-locked",
    "security_change": "authentik_core-security-alert"
}


async def sync_all_emails():
    """Sincroniza todas las plantillas a Authentik"""

    authentik_host = os.getenv("AUTHENTIK_HOST", "http://auth.casmart.internal")
    authentik_token = os.getenv("AUTHENTIK_API_TOKEN")

    if not authentik_token:
        print("❌ AUTHENTIK_API_TOKEN no configurado")
        print("   export AUTHENTIK_API_TOKEN='<token>'")
        return False

    print(f"🔗 Conectando a Authentik: {authentik_host}")
    print(f"📧 Sincronizando {len(EMAIL_EVENT_TYPES)} plantillas de email...\n")

    success_count = 0
    fail_count = 0

    async with engine.begin() as conn:
        for event_type in sorted(EMAIL_EVENT_TYPES):
            # Obtener template de BD
            result = await conn.execute(
                select(TenantEmailBody).where(
                    TenantEmailBody.event_type == event_type
                ).limit(1)
            )
            email_body = result.scalar_one_or_none()

            if not email_body:
                print(f"⚠️  {event_type:20} No template found in DB")
                continue

            template_name = AUTHENTIK_TEMPLATE_MAP.get(event_type)

            # Sincronizar a Authentik
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
                        print(f"✅ {event_type:20} → {template_name}")
                        success_count += 1
                    elif response.status_code == 404:
                        print(f"⚠️  {event_type:20} Template not found in Authentik")
                        print(f"   Expected: {template_name}")
                        fail_count += 1
                    else:
                        print(f"❌ {event_type:20} HTTP {response.status_code}")
                        error_text = response.text[:100] if response.text else "No error text"
                        print(f"   {error_text}")
                        fail_count += 1

            except httpx.TimeoutException:
                print(f"❌ {event_type:20} Timeout - Authentik unreachable")
                print(f"   {authentik_host}")
                fail_count += 1
            except Exception as e:
                print(f"❌ {event_type:20} {str(e)[:80]}")
                fail_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Synced: {success_count} | ❌ Failed: {fail_count}")
    print(f"{'='*60}")

    return fail_count == 0


if __name__ == "__main__":
    result = asyncio.run(sync_all_emails())
    sys.exit(0 if result else 1)
