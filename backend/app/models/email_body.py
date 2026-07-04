import uuid
from sqlalchemy import String, Text, CheckConstraint, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

EMAIL_EVENT_TYPES = frozenset(
    ['password_reset', 'new_account', 'account_lockout', 'email_verification', 'security_change',
     'account_locked_admin', 'account_unlocked_admin',
     'login_success', 'suspicious_request', 'invitation_used', 'app_authorized',
     'impersonation_started', 'account_deleted']
)


class TenantEmailBody(Base):
    __tablename__ = "tenant_email_bodies"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'flow_slug', 'event_type', name='uq_email_bodies_tenant_flow_event'),
        CheckConstraint(
            "event_type IN ('password_reset','new_account','account_lockout',"
            "'email_verification','security_change','account_locked_admin',"
            "'account_unlocked_admin','login_success','suspicious_request',"
            "'invitation_used','app_authorized','impersonation_started',"
            "'account_deleted')",
            name='ck_email_bodies_event_type'
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
    flow_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False, default='')
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default='')
