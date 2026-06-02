import uuid
from sqlalchemy import String, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

EMAIL_EVENT_TYPES = frozenset(
    ['password_reset', 'new_account', 'account_lockout', 'email_verification', 'security_change']
)


class TenantEmailBody(Base):
    __tablename__ = "tenant_email_bodies"
    __table_args__ = (
        UniqueConstraint('flow_slug', 'event_type', name='uq_email_bodies_flow_event'),
        CheckConstraint(
            "event_type IN ('password_reset','new_account','account_lockout',"
            "'email_verification','security_change')",
            name='ck_email_bodies_event_type'
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    flow_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False, default='')
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default='')
