#!/usr/bin/env python3
"""
Backfill de compatibilidad para tenant_applications (migración
022_add_tenant_applications).

Reproduce EXACTAMENTE el filtro hardcodeado que list_authentik_applications
tenía antes de esa migración (if "teca" in domain/name -> solo apps "teca";
elif "usana" -> solo apps "usana"; else -> todo menos usana/teca), para que
los tenants que ya existían no pierdan de golpe las apps que veían en el
panel. Deliberadamente NO se deriva de tenant_themes: esa tabla ya estaba
contaminada por el bug que esta migración corrige (el auto-registro de
temas corría para TODAS las apps de Authentik sin importar el tenant activo).

Idempotente: usa ON CONFLICT DO NOTHING sobre (tenant_id, application_slug).
Tenants nuevos (creados después de este backfill) no lo necesitan — se
enlazan solos vía _auto_link_unassigned_applications (admin.py) o
manualmente desde la pestaña Aplicaciones del panel.

Uso:
    python scripts/backfill_tenant_applications.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.future import select

from app.database import engine
from app.models.tenant import Tenant
from app.models.tenant_application import TenantApplication
from app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

authentik_engine = create_async_engine(
    settings.DATABASE_URL.replace("authentik_login_manager", "authentik"),
    echo=False,
    pool_pre_ping=True,
)


async def backfill():
    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with AsyncSessionLocal() as db:
        tenants = (await db.execute(select(Tenant))).scalars().all()

        async with authentik_engine.connect() as conn:
            result = await conn.execute(text("SELECT slug, name FROM authentik_core_application;"))
            apps = [{"slug": row[0], "name": row[1]} for row in result.fetchall()]

        created = 0
        for tenant in tenants:
            domain = (tenant.domain_pattern or "").lower()
            name = (tenant.name or "").lower()

            if "teca" in domain or "teca" in name or "tribunal" in name:
                visible = [a for a in apps if "teca" in a["slug"].lower() or "teca" in a["name"].lower()]
            elif "usana" in domain or "usana" in name:
                visible = [a for a in apps if "usana" in a["slug"].lower() or "usana" in a["name"].lower()]
            else:
                visible = [
                    a for a in apps
                    if "usana" not in a["slug"].lower() and "usana" not in a["name"].lower()
                    and "teca" not in a["slug"].lower()
                ]

            for app in visible:
                exists = (await db.execute(
                    select(TenantApplication).where(
                        TenantApplication.tenant_id == tenant.id,
                        TenantApplication.application_slug == app["slug"],
                    )
                )).scalar_one_or_none()
                if exists:
                    continue
                db.add(TenantApplication(
                    tenant_id=tenant.id,
                    application_slug=app["slug"],
                    application_name=app["name"],
                    link_source="manual",
                    is_confirmed=True,
                ))
                created += 1
                print(f"  + {tenant.name} -> {app['slug']}")

        await db.commit()
        print(f"\nBackfill completo: {created} enlaces creados.")


if __name__ == "__main__":
    asyncio.run(backfill())
