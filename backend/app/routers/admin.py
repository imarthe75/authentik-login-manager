from typing import List
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from app.database import get_db
from app.config import settings
from app.models.tenant_theme import TenantTheme
from app.schemas.theme import ThemeCreate, ThemeUpdate, ThemeResponse
from app.cache import cache

router = APIRouter(prefix="/api/v1/themes", tags=["Admin Themes"])

# Secondary engine for querying Authentik applications dynamically
authentik_engine = create_async_engine(
    settings.DATABASE_URL.replace("authentik_login_manager", "authentik"),
    echo=False,
    pool_pre_ping=True
)

# Security dependency to verify the custom header API Key
async def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials."
        )

@router.get("/authentik/applications", dependencies=[Depends(verify_admin_key)])
async def list_authentik_applications():
    try:
        async with authentik_engine.connect() as conn:
            result = await conn.execute(text("SELECT slug, name FROM authentik_core_application ORDER BY name;"))
            return [{"slug": row[0], "name": row[1]} for row in result.fetchall()]
    except Exception as e:
        # Fallback or empty if DB connection/table does not exist yet (e.g. during early initialization)
        return []

@router.get("", response_model=List[ThemeResponse], dependencies=[Depends(verify_admin_key)])
async def list_themes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TenantTheme)
        .order_by(TenantTheme.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("", response_model=ThemeResponse, dependencies=[Depends(verify_admin_key)])
async def upsert_theme(theme_in: ThemeCreate, db: AsyncSession = Depends(get_db)):
    # Check if a theme for the given flow_slug and app_slug already exists to perform upsert
    if theme_in.authentik_app_slug:
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == theme_in.authentik_flow_slug,
            TenantTheme.authentik_app_slug == theme_in.authentik_app_slug
        )
    else:
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == theme_in.authentik_flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        )
        
    result = await db.execute(stmt)
    existing_theme = result.scalar_one_or_none()

    if existing_theme:
        # Update existing record
        for field, value in theme_in.model_dump().items():
            setattr(existing_theme, field, value)
        db.add(existing_theme)
        db_theme = existing_theme
    else:
        # Create new record
        db_theme = TenantTheme(**theme_in.model_dump())
        db.add(db_theme)

    await db.flush()
    await db.commit()
    await db.refresh(db_theme)

    # Invalidate both the direct key and the global cache key for safety
    await cache.delete(f"theme:{db_theme.authentik_flow_slug}:global")
    if db_theme.authentik_app_slug:
        await cache.delete(f"theme:{db_theme.authentik_flow_slug}:{db_theme.authentik_app_slug}")
    
    # Also invalidate using Redis keys pattern if available
    if cache.redis:
        try:
            pattern = f"theme:{db_theme.authentik_flow_slug}:*"
            keys = await cache.redis.keys(pattern)
            if keys:
                await cache.redis.delete(*keys)
        except Exception:
            pass

    return db_theme

@router.get("/{flow_slug}", response_model=ThemeResponse, dependencies=[Depends(verify_admin_key)])
async def get_theme(flow_slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TenantTheme).where(TenantTheme.authentik_flow_slug == flow_slug)
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow slug.")
    return db_theme

@router.patch("/{flow_slug}", response_model=ThemeResponse, dependencies=[Depends(verify_admin_key)])
async def patch_theme(flow_slug: str, theme_in: ThemeUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(TenantTheme).where(TenantTheme.authentik_flow_slug == flow_slug)
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow slug.")

    update_data = theme_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_theme, field, value)

    db.add(db_theme)
    await db.commit()
    await db.refresh(db_theme)

    # Invalidate cache entry
    await cache.delete(f"theme:{flow_slug}")

    return db_theme

@router.delete("/{flow_slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_key)])
async def delete_theme(flow_slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TenantTheme).where(TenantTheme.authentik_flow_slug == flow_slug)
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow slug.")

    await db.delete(db_theme)
    await db.commit()

    # Invalidate cache
    await cache.delete(f"theme:{flow_slug}")


def _hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip('#')
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    except (ValueError, IndexError):
        return "255, 255, 255"


@router.post("/{flow_slug}/deploy", dependencies=[Depends(verify_admin_key)])
async def deploy_theme(flow_slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TenantTheme).where(TenantTheme.authentik_flow_slug == flow_slug)
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow slug.")

    # Custom delimiters avoid collision with Authentik's own Jinja2 variables ({{ }}, {% %})
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

    try:
        template = env.get_template("login.html.j2")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template load error: {str(e)}")

    base_url = settings.PUBLIC_API_BASE_URL.rstrip("/")
    context = {
        "theme": db_theme,
        "logo_top_url": f"{base_url}/api/v1/public/theme/{flow_slug}/image/logo_top",
        "logo_bottom_url": f"{base_url}/api/v1/public/theme/{flow_slug}/image/logo_bottom",
        "bg_image_url": f"{base_url}/api/v1/public/theme/{flow_slug}/image/bg_image",
    }

    try:
        rendered_html = template.render(**context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template render error: {str(e)}")

    output_dir = Path("/shared/authentik/templates")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "login.html"
        output_path.write_text(rendered_html, encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot write to shared volume: {str(e)}. Ensure 'authentik-custom-templates' is mounted.",
        )

    # Invalidate Valkey cache for this flow
    await cache.delete(f"theme:{flow_slug}:global")
    if db_theme.authentik_app_slug:
        await cache.delete(f"theme:{flow_slug}:{db_theme.authentik_app_slug}")
    if cache.redis:
        try:
            pattern = f"theme:{flow_slug}:*"
            keys = await cache.redis.keys(pattern)
            if keys:
                await cache.redis.delete(*keys)
        except Exception:
            pass

    return {"status": "deployed", "path": str(output_path)}
