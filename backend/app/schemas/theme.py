import uuid
from datetime import datetime
from typing import Optional, Literal, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

HEX_COLOR_REGEX = r"^#[0-9a-fA-F]{6}$"
EMAIL_EVENT_TYPE = Literal[
    'password_reset', 'new_account', 'account_lockout',
    'email_verification', 'security_change'
]
EMAIL_TEMPLATE_TYPE = Literal['integrated', 'custom_per_event']


class EmailBodySchema(BaseModel):
    subject: str = Field('', max_length=200)
    body_html: str = Field('', max_length=50000)

    @field_validator('subject', 'body_html', mode='before')
    @classmethod
    def strip_strings(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v


class ThemeBase(BaseModel):
    display_name: str = Field(..., max_length=150)
    system_name: str = Field("CASMARTS<br>Core", max_length=150)
    system_subtitle: str = Field("Gobierno del estado de México", max_length=255)
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
    email_footer_text: Optional[str] = Field(None, max_length=255)
    email_template_type: EMAIL_TEMPLATE_TYPE = 'integrated'

    @field_validator("system_name", mode="after")
    @classmethod
    def sanitize_system_name(cls, v: str) -> str:
        for bad in ["<script", "javascript:", "onload", "onerror", "<iframe>"]:
            if bad in v.lower():
                raise ValueError(f"Dangerous content detected in system_name: {bad}")
        return v

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
    authentik_flow_slug: str = Field(..., max_length=100)
    logo_top_base64: Optional[str] = None
    logo_bottom_base64: Optional[str] = None
    bg_image_base64: Optional[str] = None
    logo_top_text: Optional[str] = None
    logo_bottom_text: Optional[str] = None


class ThemeUpdate(BaseModel):
    authentik_app_slug: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=150)
    system_name: Optional[str] = Field(None, max_length=150)
    system_subtitle: Optional[str] = Field(None, max_length=255)
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
    logo_top_text: Optional[str] = None
    logo_bottom_text: Optional[str] = None
    is_active: Optional[bool] = None
    # Access & notifications
    allow_self_registration: Optional[bool] = None
    require_email_verification: Optional[bool] = None
    show_social_google: Optional[bool] = None
    show_social_microsoft: Optional[bool] = None
    show_social_gov_id: Optional[bool] = None
    email_footer_text: Optional[str] = Field(None, max_length=255)
    email_template_type: Optional[EMAIL_TEMPLATE_TYPE] = None

    @field_validator("email_footer_text", mode="before")
    @classmethod
    def strip_footer(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode='after')
    def coerce_email_verification(self) -> 'ThemeUpdate':
        if self.allow_self_registration is False:
            self.require_email_verification = False
        return self


class ThemeUpdateWithEmail(ThemeUpdate):
    email_bodies: Optional[Dict[str, EmailBodySchema]] = None


class ThemeResponse(ThemeBase):
    id: uuid.UUID
    authentik_flow_slug: str
    logo_top_base64: Optional[str] = None
    logo_bottom_base64: Optional[str] = None
    bg_image_base64: Optional[str] = None
    logo_top_text: Optional[str] = None
    logo_bottom_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThemeResponseWithEmail(ThemeResponse):
    email_bodies: Dict[str, EmailBodySchema] = {}


class ThemePublic(BaseModel):
    display_name: str
    system_name: str
    system_subtitle: str
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
    logo_top_text: Optional[str] = None
    logo_bottom_text: Optional[str] = None
    allow_self_registration: bool = False
    show_social_google: bool = False
    show_social_microsoft: bool = False
    show_social_gov_id: bool = False
    is_custom: bool = True

    model_config = ConfigDict(from_attributes=True)
