import logging
from typing import List, Optional, Dict
import uuid
from pathlib import Path
from types import SimpleNamespace
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from app.database import get_db
from app.config import settings
from app.models.tenant_theme import TenantTheme
from app.models.email_body import TenantEmailBody, EMAIL_EVENT_TYPES
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


async def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials."
        )


# ── helpers ─────────────────────────────────────────────────────────────────

async def _load_email_bodies(flow_slug: str, db: AsyncSession) -> Dict[str, EmailBodySchema]:
    result = await db.execute(
        select(TenantEmailBody).where(TenantEmailBody.flow_slug == flow_slug)
    )
    return {
        eb.event_type: EmailBodySchema(subject=eb.subject, body_html=eb.body_html)
        for eb in result.scalars().all()
    }


async def _upsert_email_bodies(
    flow_slug: str,
    bodies: Dict[str, EmailBodySchema],
    db: AsyncSession
) -> None:
    for event_type, body in bodies.items():
        if event_type not in EMAIL_EVENT_TYPES:
            continue
        result = await db.execute(
            select(TenantEmailBody).where(
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


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get("/authentik/applications", dependencies=[Depends(verify_admin_key)])
async def list_authentik_applications():
    try:
        async with authentik_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT slug, name FROM authentik_core_application ORDER BY name;")
            )
            return [{"slug": row[0], "name": row[1]} for row in result.fetchall()]
    except Exception:
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


@router.post("", response_model=ThemeResponseWithEmail, dependencies=[Depends(verify_admin_key)])
async def upsert_theme(theme_in: ThemeCreate, db: AsyncSession = Depends(get_db)):
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
        for field, value in theme_in.model_dump().items():
            setattr(existing_theme, field, value)
        db.add(existing_theme)
        db_theme = existing_theme
    else:
        db_theme = TenantTheme(**theme_in.model_dump())
        db.add(db_theme)

    await db.flush()
    await db.commit()
    await db.refresh(db_theme)

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

    email_bodies = await _load_email_bodies(db_theme.authentik_flow_slug, db)
    return _build_theme_response_with_email(db_theme, email_bodies)


@router.get("/{flow_slug}/emails/preview/{event_type}", dependencies=[Depends(verify_admin_key)])
async def preview_email(
    flow_slug: str,
    event_type: str,
    db: AsyncSession = Depends(get_db)
):
    if event_type not in EMAIL_EVENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event_type. Must be one of: {sorted(EMAIL_EVENT_TYPES)}"
        )

    result = await db.execute(
        select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        )
    )
    theme = result.scalar_one_or_none()
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme not found for flow '{flow_slug}'.")

    eb_result = await db.execute(
        select(TenantEmailBody).where(
            TenantEmailBody.flow_slug == flow_slug,
            TenantEmailBody.event_type == event_type
        )
    )
    email_body = eb_result.scalar_one_or_none()
    body_html = email_body.body_html if email_body else ''
    subject = email_body.subject if email_body else ''

    preview_subs = {
        '{{ url }}': 'https://preview.casmarts.example/reset/TOK-PREVIEW-12345',
        '{{ user.username }}': 'usuario.ejemplo',
        '{{ user.email }}': 'usuario.ejemplo@casmarts.internal',
        '{{ token }}': 'TOK-PREVIEW-12345',
        '{{ tenant.name }}': theme.display_name,
    }
    for var, val in preview_subs.items():
        body_html = body_html.replace(var, val)

    logo_base64: Optional[str] = theme.logo_top_base64
    if logo_base64 and len(logo_base64.encode()) > 200 * 1024:
        log.warning("logo_top_base64 exceeds 200 KB for flow '%s' — omitting from email preview.", flow_slug)
        logo_base64 = None

    env = _build_email_jinja2_env()
    template = env.get_template(f'{event_type}.html.j2')
    html = template.render(
        theme=theme,
        body_html=body_html,
        subject=subject,
        logo_base64=logo_base64,
        event_type=event_type,
        cta_url='https://preview.casmarts.example/reset/TOK-PREVIEW-12345',
    )
    return HTMLResponse(content=html)


@router.get("/{flow_slug}", response_model=ThemeResponseWithEmail, dependencies=[Depends(verify_admin_key)])
async def get_theme(
    flow_slug: str,
    app_slug: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    if app_slug:
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug == app_slug
        )
    else:
        stmt = select(TenantTheme).where(
            TenantTheme.authentik_flow_slug == flow_slug,
            TenantTheme.authentik_app_slug.is_(None)
        )
    result = await db.execute(stmt)
    db_theme = result.scalar_one_or_none()
    if not db_theme:
        raise HTTPException(status_code=404, detail="Theme not found for this flow or app slug.")

    email_bodies = await _load_email_bodies(flow_slug, db)
    return _build_theme_response_with_email(db_theme, email_bodies)


@router.patch("/{flow_slug}", response_model=ThemeResponseWithEmail, dependencies=[Depends(verify_admin_key)])
async def patch_theme(
    flow_slug: str,
    theme_in: ThemeUpdateWithEmail,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TenantTheme).where(TenantTheme.authentik_flow_slug == flow_slug)
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
        await _upsert_email_bodies(flow_slug, bodies, db)

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

    email_bodies = await _load_email_bodies(flow_slug, db)
    return _build_theme_response_with_email(db_theme, email_bodies)


@router.delete("/{flow_slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_key)])
async def delete_theme(flow_slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TenantTheme).where(TenantTheme.authentik_flow_slug == flow_slug)
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
    email_footer_text=None,
    email_template_type='integrated',
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
    return template.render(
        theme=theme,
        api_base=api_base,
        logo_top_url=f'{api_base}/api/v1/public/theme/{flow_slug}/image/logo_top{app_qs}' if getattr(theme, 'logo_top_base64', None) else '',
        logo_bottom_url=f'{api_base}/api/v1/public/theme/{flow_slug}/image/logo_bottom{app_qs}' if getattr(theme, 'logo_bottom_base64', None) else '',
        bg_image_url=f'{api_base}/api/v1/public/theme/{flow_slug}/image/bg_image{app_qs}' if getattr(theme, 'bg_image_base64', None) else '',
    )


def _build_universal_template(
    app_themes: list[tuple[str, TenantTheme]],
    global_theme,
) -> str:
    env = _build_jinja2_env()
    fallback = global_theme if global_theme else (app_themes[0][1] if app_themes else _DEFAULT_THEME)
    return _render_theme(env, fallback)


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

    deployed_apps = [slug for slug, _ in app_themes] or (["(global)"] if global_theme else [])
    return {
        "status": "deployed",
        "path": str(output_path),
        "apps": deployed_apps,
    }
