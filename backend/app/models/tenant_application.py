import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, CheckConstraint, UniqueConstraint, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

LINK_SOURCES = frozenset(["group_convention", "manual"])


class TenantApplication(Base):
    """
    Enlace explícito entre una Application de Authentik (por slug) y el
    Tenant al que pertenece. Fuente de verdad para "qué apps ve cada
    tenant" — reemplaza el filtro por substring de nombre que había en
    list_authentik_applications (admin.py) y el set KNOWN_APP_SLUGS
    hardcodeado en authentik_events.py.
    """
    __tablename__ = "tenant_applications"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'application_slug', name='uq_tenant_applications_tenant_app'),
        CheckConstraint(
            "link_source IN ('group_convention','manual')",
            name='ck_tenant_applications_link_source'
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    application_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    application_name: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    link_source: Mapped[str] = mapped_column(String(20), nullable=False, default='manual')
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
