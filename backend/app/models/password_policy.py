import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

# Fila única (singleton): Authentik solo tiene UNA PasswordPolicy global
# (default-password-change-password-policy) compartida por los flujos
# default-authentication-flow, default-password-change y password-recovery
# — no existe hoy el concepto de política por tenant.
SINGLETON_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class PasswordPolicy(Base):
    __tablename__ = "password_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    length_min: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    amount_uppercase: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount_lowercase: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_digits: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount_symbols: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    symbol_charset: Mapped[str] = mapped_column(Text, nullable=False)
    check_zxcvbn: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    zxcvbn_score_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    check_have_i_been_pwned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Cuántas veces puede aparecer la contraseña en brechas conocidas antes de
    # rechazarla — 0 (default real de Authentik) es lo más estricto: rechaza
    # con una sola aparición.
    hibp_allowed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str] = mapped_column(String(500), nullable=False)
    # Texto de ayuda mostrado bajo el campo de nueva contraseña (Authentik
    # Prompt.sub_text) — visible ANTES de escribir, a diferencia de
    # error_message que solo aparece tras un rechazo.
    help_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Expiración de contraseña: modela un tipo de policy DISTINTO en Authentik
    # (authentik_policies_expiry.PasswordExpiryPolicy + PolicyBinding en el
    # stage de password del login), no un campo de PasswordPolicy — ver
    # _sync_expiry_policy en el router.
    expiry_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expiry_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    # Vigencia del enlace de un solo uso para establecer/recuperar contraseña
    # — sincronizado con EmailStage('casmarts-smtp-gmail').token_expiry, y
    # con el texto informativo de los correos password_reset/new_account
    # (login-manager), que comparten ese mismo enlace/flujo.
    link_expiry_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    # Intentos fallidos de login permitidos antes de bloquear la cuenta —
    # sincronizado con ReputationPolicy('casmarts-lockout-reputation').threshold
    # en Authentik (threshold = -lockout_failed_attempts; cada login_failed
    # resta 1 punto, ver authentik/policies/reputation/signals.py) y usado
    # también por _is_account_locked_out en authentik_events.py para
    # reevaluar si un login_failed real ya cruzó el umbral.
    lockout_failed_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
