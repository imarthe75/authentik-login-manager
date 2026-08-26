import uuid
import bleach
from datetime import datetime
from typing import Optional, Literal, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from app.font_presets import FONT_PRESETS

HEX_COLOR_REGEX = r"^#[0-9a-fA-F]{6}$"
FONT_KEY_LITERAL = Literal[tuple(FONT_PRESETS.keys())]
EMAIL_EVENT_TYPE = Literal[
    'password_reset', 'new_account', 'account_lockout',
    'email_verification', 'security_change'
]
EMAIL_TEMPLATE_TYPE = Literal['integrated', 'custom_per_event']

# system_name/logo_top_text/logo_bottom_text se renderizan SIN escapar
# (innerHTML) en la página de login real vista por usuarios finales — no solo
# en el preview del admin. Solo documentan soportar <br> (salto de línea), no
# texto enriquecido general, así que se usa un allowlist estricto (bleach) en
# vez de un denylist de patrones peligrosos (bypasseable, ej. onmouseover=,
# <svg onload=>, etc. no cubiertos por una lista fija de palabras).
_ALLOWED_TEXT_TAGS = ['br']


def _sanitize_html_fragment(v: Optional[str]) -> Optional[str]:
    """
    Sanitiza fragmentos de texto HTML para evitar vulnerabilidades XSS.
    Solo permite el uso de etiquetas de salto de línea (<br>).
    """
    if v is None:
        return v
    return bleach.clean(v, tags=_ALLOWED_TEXT_TAGS, attributes={}, strip=True)


def _sanitize_message_dict(v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    custom_messages se embebe como JSON dentro de un bloque <script> en la
    página de login real (ver login.html.j2, CUSTOM_TRANSLATIONS) — no admite
    ni siquiera <br>, a diferencia de system_name/system_subtitle que se
    escriben via innerHTML fuera de un <script>.
    """
    if not v:
        return v
    return {
        str(k): bleach.clean(str(val), tags=[], attributes={}, strip=True)
        for k, val in v.items()
    }


class EmailBodySchema(BaseModel):
    """
    Esquema para definir el asunto y el cuerpo HTML de un correo electrónico.
    """
    subject: str = Field('', max_length=200)
    body_html: str = Field('', max_length=50000)

    @field_validator('subject', 'body_html', mode='before')
    @classmethod
    def strip_strings(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v


class ThemeBase(BaseModel):
    """
    Esquema base que define la configuración de diseño visual, colores,
    opacidades y flags de características de un tema de tenant.
    """
    display_name: str = Field(..., max_length=150)
    system_name: str = Field("CASMARTS<br>Core", max_length=150)
    system_subtitle: str = Field("Autenticación Unificada", max_length=255)
    system_name_color: str = Field("#111827", pattern=HEX_COLOR_REGEX)
    system_subtitle_color: str = Field("#374151", pattern=HEX_COLOR_REGEX)
    field_label_color: str = Field("#374151", pattern=HEX_COLOR_REGEX)
    font_heading: FONT_KEY_LITERAL = "inter"
    font_body: FONT_KEY_LITERAL = "inter"
    layout_position: Literal["left", "center", "right"] = "left"
    name_align: Literal["left", "center", "right"] = "center"
    subtitle_align: Literal["left", "center", "right"] = "center"
    privacy_align: Literal["left", "center", "right"] = "center"
    primary_color: str = Field("#4272A5", pattern=HEX_COLOR_REGEX)
    hover_color: str = Field("#2d5580", pattern=HEX_COLOR_REGEX)
    card_bg_color: str = Field("#FFFFFF", pattern=HEX_COLOR_REGEX)
    panel_bg_color: str = Field("#F6F9FD", pattern=HEX_COLOR_REGEX)
    bg_type: Literal["gradient", "color", "image"] = "gradient"
    bg_flat_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    bg_gradient_from: str = Field("#c8c4bc", pattern=HEX_COLOR_REGEX)
    bg_gradient_to: str = Field("#a09890", pattern=HEX_COLOR_REGEX)
    bg_opacity: float = Field(1.0, ge=0.0, le=1.0)
    form_opacity: float = Field(0.55, ge=0.0, le=1.0)
    form_height_pct: Optional[int] = Field(None, ge=0, le=100)
    logos_opacity: float = Field(0.55, ge=0.0, le=1.0)
    logos_height_pct: Optional[int] = Field(None, ge=0, le=100)
    privacy_pdf_url: Optional[str] = Field(None, max_length=512)
    authentik_app_slug: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    # Access & notifications
    allow_self_registration: bool = False
    require_email_verification: bool = True
    show_social_google: bool = False
    show_social_microsoft: bool = False
    show_social_gov_id: bool = False
    show_forgot_password: bool = True
    show_logos_panel: bool = True
    show_password_toggle: bool = True
    show_system_name: bool = True
    show_system_subtitle: bool = True
    show_field_labels: bool = True
    show_app_message: bool = False
    email_footer_text: Optional[str] = Field(None, max_length=255)
    email_template_type: EMAIL_TEMPLATE_TYPE = 'integrated'
    custom_messages: Optional[Dict[str, str]] = Field(default_factory=dict)
    expansion_config: Optional[Dict] = Field(default_factory=dict)

    @field_validator("system_name", "system_subtitle", mode="after")
    @classmethod
    def sanitize_system_name(cls, v: str) -> str:
        return _sanitize_html_fragment(v)

    @field_validator("custom_messages", mode="after")
    @classmethod
    def sanitize_custom_messages(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        return _sanitize_message_dict(v)

    @field_validator("email_footer_text", mode="before")
    @classmethod
    def strip_footer(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode='after')
    def coerce_email_verification(self) -> 'ThemeBase':
        if not self.allow_self_registration:
            self.require_email_verification = False
        return self


class ThemeCreate(ThemeBase):
    """
    Esquema utilizado para la creación de un nuevo tema de tenant,
    el cual incluye recursos pesados (imágenes en formato Base64) y slugs de Authentik.
    """
    authentik_flow_slug: str = Field(..., max_length=100)
    logo_top_base64: Optional[str] = None
    logo_bottom_base64: Optional[str] = None
    bg_image_base64: Optional[str] = None
    favicon_base64: Optional[str] = None
    custom_font_heading_base64: Optional[str] = None
    custom_font_heading_name: Optional[str] = Field(None, max_length=100)
    custom_font_body_base64: Optional[str] = None
    custom_font_body_name: Optional[str] = Field(None, max_length=100)
    logo_top_text: Optional[str] = Field(None, max_length=150)
    logo_bottom_text: Optional[str] = Field(None, max_length=150)
    logo_top_text_color: str = Field("#FFFFFF", pattern=HEX_COLOR_REGEX)
    logo_top_text_size: int = Field(24, ge=10, le=60)
    logo_bottom_text_color: str = Field("#FFFFFF", pattern=HEX_COLOR_REGEX)
    logo_bottom_text_size: int = Field(20, ge=10, le=60)

    @field_validator("logo_top_text", "logo_bottom_text", mode="after")
    @classmethod
    def sanitize_logo_texts(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_html_fragment(v)


class ThemeUpdate(BaseModel):
    """
    Esquema que permite la actualización parcial (patch) de la configuración
    del tema de un tenant. Todos los campos son opcionales.
    """
    authentik_app_slug: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=150)
    system_name: Optional[str] = Field(None, max_length=150)
    system_subtitle: Optional[str] = Field(None, max_length=255)
    system_name_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    system_subtitle_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    field_label_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    font_heading: Optional[FONT_KEY_LITERAL] = None
    font_body: Optional[FONT_KEY_LITERAL] = None
    custom_font_heading_base64: Optional[str] = None
    custom_font_heading_name: Optional[str] = Field(None, max_length=100)
    custom_font_body_base64: Optional[str] = None
    custom_font_body_name: Optional[str] = Field(None, max_length=100)
    layout_position: Optional[Literal["left", "center", "right"]] = None
    name_align: Optional[Literal["left", "center", "right"]] = None
    subtitle_align: Optional[Literal["left", "center", "right"]] = None
    privacy_align: Optional[Literal["left", "center", "right"]] = None
    primary_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    hover_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    card_bg_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    panel_bg_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    bg_type: Optional[Literal["gradient", "color", "image"]] = None
    bg_flat_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    bg_gradient_from: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    bg_gradient_to: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    bg_opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    form_opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    form_height_pct: Optional[int] = Field(None, ge=0, le=100)
    logos_opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    logos_height_pct: Optional[int] = Field(None, ge=0, le=100)
    privacy_pdf_url: Optional[str] = Field(None, max_length=512)
    logo_top_base64: Optional[str] = None
    logo_bottom_base64: Optional[str] = None
    bg_image_base64: Optional[str] = None
    favicon_base64: Optional[str] = None
    logo_top_text: Optional[str] = Field(None, max_length=150)
    logo_bottom_text: Optional[str] = Field(None, max_length=150)
    logo_top_text_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    logo_top_text_size: Optional[int] = Field(None, ge=10, le=60)
    logo_bottom_text_color: Optional[str] = Field(None, pattern=HEX_COLOR_REGEX)
    logo_bottom_text_size: Optional[int] = Field(None, ge=10, le=60)
    is_active: Optional[bool] = None
    # Access & notifications
    allow_self_registration: Optional[bool] = None
    require_email_verification: Optional[bool] = None
    show_social_google: Optional[bool] = None
    show_social_microsoft: Optional[bool] = None
    show_social_gov_id: Optional[bool] = None
    show_forgot_password: Optional[bool] = None
    show_logos_panel: Optional[bool] = None
    show_password_toggle: Optional[bool] = None
    show_system_name: Optional[bool] = None
    show_system_subtitle: Optional[bool] = None
    show_field_labels: Optional[bool] = None
    show_app_message: Optional[bool] = None
    email_footer_text: Optional[str] = Field(None, max_length=255)
    email_template_type: Optional[EMAIL_TEMPLATE_TYPE] = None
    custom_messages: Optional[Dict[str, str]] = None
    expansion_config: Optional[Dict] = None

    @field_validator("email_footer_text", mode="before")
    @classmethod
    def strip_footer(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @field_validator("system_name", "system_subtitle", "logo_top_text", "logo_bottom_text", mode="after")
    @classmethod
    def sanitize_text_fragments(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_html_fragment(v)

    @field_validator("custom_messages", mode="after")
    @classmethod
    def sanitize_custom_messages(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        return _sanitize_message_dict(v)

    @model_validator(mode='after')
    def coerce_email_verification(self) -> 'ThemeUpdate':
        if self.allow_self_registration is False:
            self.require_email_verification = False
        return self


class ThemeUpdateWithEmail(ThemeUpdate):
    """
    Esquema extendido de actualización que permite modificar tanto el tema
    como los cuerpos de los correos electrónicos vinculados.
    """
    email_bodies: Optional[Dict[str, EmailBodySchema]] = None


class ThemeResponse(ThemeBase):
    """
    Esquema de respuesta detallado que devuelve toda la configuración de un tema,
    incluyendo su ID de base de datos y timestamps.
    """
    id: uuid.UUID
    authentik_flow_slug: str
    logo_top_base64: Optional[str] = None
    logo_bottom_base64: Optional[str] = None
    bg_image_base64: Optional[str] = None
    favicon_base64: Optional[str] = None
    custom_font_heading_base64: Optional[str] = None
    custom_font_heading_name: Optional[str] = None
    custom_font_body_base64: Optional[str] = None
    custom_font_body_name: Optional[str] = None
    logo_top_text: Optional[str] = Field(None, max_length=150)
    logo_bottom_text: Optional[str] = Field(None, max_length=150)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    # Defensa en profundidad: limpia también en lectura, por si hay filas ya
    # persistidas antes de este fix (bleach.clean es idempotente — no rompe
    # contenido ya limpio).
    @field_validator("logo_top_text", "logo_bottom_text", mode="after")
    @classmethod
    def sanitize_logo_texts(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_html_fragment(v)


class ThemeResponseWithEmail(ThemeResponse):
    email_bodies: Dict[str, EmailBodySchema] = {}
    # Solo se completan cuando el tema guardado es el GLOBAL del tenant
    # (authentik_app_slug=None) y trae favicon_base64: ese caso empuja el
    # favicon al Brand nativo de Authentik (por dominio) además de guardarlo
    # aquí — ver _push_favicon_to_authentik_brand en routers/admin.py.
    favicon_synced_to_authentik: Optional[bool] = None
    favicon_sync_error: Optional[str] = None


class ThemePublic(BaseModel):
    """
    Esquema de respuesta simplificado expuesto públicamente para la interfaz de login,
    sustituyendo los datos Base64 pesados por booleanos de presencia (`has_*`).
    """
    display_name: str
    system_name: str
    system_subtitle: str
    system_name_color: str = "#111827"
    system_subtitle_color: str = "#374151"
    field_label_color: str = "#374151"
    font_heading_family: str = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
    font_body_family: str = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
    font_heading_import_url: Optional[str] = None
    font_body_import_url: Optional[str] = None
    has_custom_font_heading: bool = False
    has_custom_font_body: bool = False
    layout_position: str
    name_align: str
    subtitle_align: str
    privacy_align: str
    primary_color: str
    hover_color: str
    card_bg_color: str
    panel_bg_color: str
    bg_type: str
    bg_flat_color: Optional[str] = None
    bg_gradient_from: str
    bg_gradient_to: str
    bg_opacity: float
    form_opacity: float
    form_height_pct: Optional[int] = None
    logos_opacity: float
    logos_height_pct: Optional[int] = None
    privacy_pdf_url: Optional[str] = None
    authentik_app_slug: Optional[str] = None
    has_logo_top: bool
    has_logo_bottom: bool
    has_bg_image: bool
    has_favicon: bool = False
    logo_top_text: Optional[str] = Field(None, max_length=150)
    logo_bottom_text: Optional[str] = Field(None, max_length=150)
    logo_top_text_color: str = "#FFFFFF"
    logo_top_text_size: int = 24
    logo_bottom_text_color: str = "#FFFFFF"
    logo_bottom_text_size: int = 20
    allow_self_registration: bool = False
    show_social_google: bool = False
    show_social_microsoft: bool = False
    show_social_gov_id: bool = False
    show_forgot_password: bool = True
    show_logos_panel: bool = True
    show_password_toggle: bool = True
    show_system_name: bool = True
    show_system_subtitle: bool = True
    show_field_labels: bool = True
    show_app_message: bool = False
    is_custom: bool = True
    custom_messages: Optional[Dict[str, str]] = Field(default_factory=dict)
    expansion_config: Optional[Dict] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    # ThemePublic alimenta directamente la página de login real (no solo el
    # preview del admin) — misma defensa en profundidad que ThemeResponse.
    @field_validator("system_name", "system_subtitle", "logo_top_text", "logo_bottom_text", mode="after")
    @classmethod
    def sanitize_text_fragments(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_html_fragment(v)

    @field_validator("custom_messages", mode="after")
    @classmethod
    def sanitize_custom_messages(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        return _sanitize_message_dict(v)
