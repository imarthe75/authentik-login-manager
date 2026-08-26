import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, func, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class TenantTheme(Base):
    """
    Representa el tema de diseño visual y configuración de la interfaz de login
    asociado a un Tenant (inquilino) específico en la integración con Authentik.

    Define colores, alineaciones, logotipos, visibilidad de elementos (botones, links)
    y flujos específicos de autenticación para cada tenant de manera dinámica.
    """
    __tablename__ = "tenant_themes"

    # Identificadores y Relaciones
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    # Slugs de vinculación con flujos y aplicaciones de Authentik
    authentik_flow_slug: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    authentik_app_slug: Mapped[str | None] = mapped_column(
        String(100), index=True, nullable=True
    )

    # Textos de la Interfaz de Usuario (UI)
    display_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )
    system_name: Mapped[str] = mapped_column(
        String(150), default="CASMARTS<br>Core", nullable=False
    )
    system_subtitle: Mapped[str] = mapped_column(
        String(255), default="Autenticación Unificada", nullable=False
    )
    system_name_color: Mapped[str] = mapped_column(
        String(7), default="#111827", server_default="#111827", nullable=False
    )
    system_subtitle_color: Mapped[str] = mapped_column(
        String(7), default="#374151", server_default="#374151", nullable=False
    )

    # Disposición y Alineaciones
    layout_position: Mapped[str] = mapped_column(
        String(10), default="left", nullable=False
    )
    name_align: Mapped[str] = mapped_column(
        String(10), default="center", nullable=False
    )
    subtitle_align: Mapped[str] = mapped_column(
        String(10), default="center", nullable=False
    )
    privacy_align: Mapped[str] = mapped_column(
        String(10), default="center", nullable=False
    )

    # Paleta de Colores Básica
    primary_color: Mapped[str] = mapped_column(
        String(7), default="#4272A5", nullable=False
    )
    hover_color: Mapped[str] = mapped_column(
        String(7), default="#2d5580", nullable=False
    )
    card_bg_color: Mapped[str] = mapped_column(
        String(7), default="#FFFFFF", nullable=False
    )
    panel_bg_color: Mapped[str] = mapped_column(
        String(7), default="#F6F9FD", nullable=False
    )

    # Configuración de Fondo
    bg_type: Mapped[str] = mapped_column(
        String(10), default="gradient", nullable=False
    )
    bg_flat_color: Mapped[str | None] = mapped_column(
        String(7), nullable=True
    )
    bg_gradient_from: Mapped[str] = mapped_column(
        String(7), default="#c8c4bc", nullable=False
    )
    bg_gradient_to: Mapped[str] = mapped_column(
        String(7), default="#a09890", nullable=False
    )
    bg_image_base64: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Opacidades y Dimensiones de Elementos Visuales
    bg_opacity: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    form_opacity: Mapped[float] = mapped_column(
        Float, default=0.55, nullable=False
    )
    form_height_pct: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    logos_opacity: Mapped[float] = mapped_column(
        Float, default=0.55, nullable=False
    )
    logos_height_pct: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Logotipos y Textos de Marca (Soporte Base64)
    logo_top_base64: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    logo_bottom_base64: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    favicon_base64: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    logo_top_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    logo_bottom_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    logo_top_text_color: Mapped[str] = mapped_column(
        String(7), default="#FFFFFF", server_default="#FFFFFF", nullable=False
    )
    logo_top_text_size: Mapped[int] = mapped_column(
        Integer, default=24, server_default="24", nullable=False
    )
    logo_bottom_text_color: Mapped[str] = mapped_column(
        String(7), default="#FFFFFF", server_default="#FFFFFF", nullable=False
    )
    logo_bottom_text_size: Mapped[int] = mapped_column(
        Integer, default=20, server_default="20", nullable=False
    )
    # Etiquetas de campo ("Correo o Nombre usuario", "Contraseña") — antes
    # fijas en rgba(0,0,0,0.7) sin importar el tema, por lo que se volvían
    # ilegibles en tarjetas de fondo oscuro (ver caso centinela-ai).
    field_label_color: Mapped[str] = mapped_column(
        String(7), default="#374151", server_default="#374151", nullable=False
    )

    # Tipografía (heading = system_name/logos, body = formulario/labels).
    # Keys deben existir en app.font_presets.FONT_PRESETS. Las entradas
    # *_base64/_name solo se usan cuando el preset elegido es de licencia
    # propia (requires_upload=True, ej. Gotham/BW Modelica/Corporative Sans
    # Alt del manual de identidad EdoMex) — no se puede hotlinkear esas
    # fuentes desde un CDN público.
    font_heading: Mapped[str] = mapped_column(
        String(30), default="inter", server_default="inter", nullable=False
    )
    font_body: Mapped[str] = mapped_column(
        String(30), default="inter", server_default="inter", nullable=False
    )
    custom_font_heading_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_font_heading_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_font_body_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_font_body_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Políticas de Privacidad y Estado Activo
    privacy_pdf_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Registro y Verificación de Usuarios
    allow_self_registration: Mapped[bool] = mapped_column(
        Boolean, server_default='false', nullable=False
    )
    require_email_verification: Mapped[bool] = mapped_column(
        Boolean, server_default='true', nullable=False
    )

    # Proveedores de Autenticación Social (OAuth2)
    show_social_google: Mapped[bool] = mapped_column(
        Boolean, server_default='false', nullable=False
    )
    show_social_microsoft: Mapped[bool] = mapped_column(
        Boolean, server_default='false', nullable=False
    )
    show_social_gov_id: Mapped[bool] = mapped_column(
        Boolean, server_default='false', nullable=False
    )

    # Elementos Visibles y Controles de Interfaz
    show_forgot_password: Mapped[bool] = mapped_column(
        Boolean, server_default='true', nullable=False
    )
    show_logos_panel: Mapped[bool] = mapped_column(
        Boolean, server_default='true', nullable=False
    )
    show_password_toggle: Mapped[bool] = mapped_column(
        Boolean, server_default='true', nullable=False
    )
    show_system_name: Mapped[bool] = mapped_column(
        Boolean, server_default='true', nullable=False
    )
    show_system_subtitle: Mapped[bool] = mapped_column(
        Boolean, server_default='true', nullable=False
    )
    show_field_labels: Mapped[bool] = mapped_column(
        Boolean, server_default='true', nullable=False
    )
    show_app_message: Mapped[bool] = mapped_column(
        Boolean, server_default='false', nullable=False
    )

    # Configuración de Plantillas de Email y Mensajes
    email_footer_text: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    email_template_type: Mapped[str] = mapped_column(
        String(20), server_default='integrated', nullable=False
    )
    custom_messages: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, server_default='{}'
    )
    expansion_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, server_default='{}'
    )

    # Auditoría y Tiempos de Registro
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
