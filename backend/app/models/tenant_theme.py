import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class TenantTheme(Base):
    __tablename__ = "tenant_themes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    authentik_flow_slug: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    authentik_app_slug: Mapped[str | None] = mapped_column(
        String(100), index=True, nullable=True
    )
    display_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )
    system_name: Mapped[str] = mapped_column(
        String(150), default="CASMARTS<br>Core", nullable=False
    )
    system_subtitle: Mapped[str] = mapped_column(
        String(255), default="Gobierno del estado de México", nullable=False
    )
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
    logo_top_base64: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    logo_bottom_base64: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    logo_top_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    logo_bottom_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    privacy_pdf_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
