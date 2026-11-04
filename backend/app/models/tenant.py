import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # server_default (no default= de Python): postgres/rules.md #2 exige
    # uuidv7, no uuid4; necesario para que SQLAlchemy pida el valor generado
    # de vuelta via RETURNING (ver tenant_application.py, mismo patron).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    domain_pattern: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    logo_email_base64: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    primary_color: Mapped[str] = mapped_column(
        String(7), default="#4272A5", nullable=False
    )
    secondary_color: Mapped[str] = mapped_column(
        String(7), default="#2d5580", nullable=False
    )
    config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, server_default='{}'
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
