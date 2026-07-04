import html
import uuid
import bleach
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# error_message/help_text terminan como texto plano dentro del formulario de
# Authentik (Prompt.sub_text / PasswordPolicy.error_message) — se despojan de
# tags por defensa en profundidad, igual que el resto de campos de texto libre
# del proyecto (ver schemas/theme.py). A diferencia de esos campos, este texto
# NO se inyecta como innerHTML en ningún lado nuestro (va vía API JSON a
# Authentik, que renderiza texto plano escapado por su propio frontend lit-html)
# — por eso se revierte el entity-encoding que bleach.clean() aplica al
# reserializar el texto sobreviviente, para no guardar literales "&amp;" visibles.
def _strip_html(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    return html.unescape(bleach.clean(v, tags=[], attributes={}, strip=True)).strip()


class PasswordPolicyBase(BaseModel):
    length_min: int = Field(10, ge=4, le=128)
    amount_uppercase: int = Field(1, ge=0, le=20)
    amount_lowercase: int = Field(0, ge=0, le=20)
    amount_digits: int = Field(1, ge=0, le=20)
    amount_symbols: int = Field(0, ge=0, le=20)
    symbol_charset: str = Field(..., min_length=1, max_length=200)
    check_zxcvbn: bool = True
    zxcvbn_score_threshold: int = Field(3, ge=0, le=4)
    check_have_i_been_pwned: bool = False
    hibp_allowed_count: int = Field(0, ge=0, le=100)
    error_message: str = Field(..., min_length=1, max_length=500)
    help_text: str = Field(..., min_length=1, max_length=1000)
    expiry_enabled: bool = False
    expiry_days: int = Field(90, ge=1, le=3650)
    link_expiry_minutes: int = Field(60, ge=1, le=10080)
    lockout_failed_attempts: int = Field(5, ge=1, le=50)

    # symbol_charset NO pasa por sanitize_text: es un conjunto literal de
    # caracteres que Authentik usa para validar símbolos, no texto para
    # mostrar — incluye intencionalmente un espacio final; despojarlo de
    # HTML o recortarlo (.strip()) corrompería el conjunto real.
    @field_validator('error_message', 'help_text', mode='before')
    @classmethod
    def sanitize_text(cls, v: object) -> object:
        return _strip_html(v) if isinstance(v, str) else v


class PasswordPolicyUpdate(BaseModel):
    """Todos los campos opcionales: PATCH solo aplica lo enviado."""
    length_min: Optional[int] = Field(None, ge=4, le=128)
    amount_uppercase: Optional[int] = Field(None, ge=0, le=20)
    amount_lowercase: Optional[int] = Field(None, ge=0, le=20)
    amount_digits: Optional[int] = Field(None, ge=0, le=20)
    amount_symbols: Optional[int] = Field(None, ge=0, le=20)
    symbol_charset: Optional[str] = Field(None, min_length=1, max_length=200)
    check_zxcvbn: Optional[bool] = None
    zxcvbn_score_threshold: Optional[int] = Field(None, ge=0, le=4)
    check_have_i_been_pwned: Optional[bool] = None
    hibp_allowed_count: Optional[int] = Field(None, ge=0, le=100)
    error_message: Optional[str] = Field(None, min_length=1, max_length=500)
    help_text: Optional[str] = Field(None, min_length=1, max_length=1000)
    expiry_enabled: Optional[bool] = None
    expiry_days: Optional[int] = Field(None, ge=1, le=3650)
    link_expiry_minutes: Optional[int] = Field(None, ge=1, le=10080)
    lockout_failed_attempts: Optional[int] = Field(None, ge=1, le=50)

    # symbol_charset NO pasa por sanitize_text: es un conjunto literal de
    # caracteres que Authentik usa para validar símbolos, no texto para
    # mostrar — incluye intencionalmente un espacio final; despojarlo de
    # HTML o recortarlo (.strip()) corrompería el conjunto real.
    @field_validator('error_message', 'help_text', mode='before')
    @classmethod
    def sanitize_text(cls, v: object) -> object:
        return _strip_html(v) if isinstance(v, str) else v


class PasswordPolicyResponse(PasswordPolicyBase):
    id: uuid.UUID
    last_synced_at: Optional[datetime] = None
    updated_at: datetime
    # Estado de la última sincronización hacia Authentik en ESTA request
    # (None si esta respuesta viene de un GET simple, sin intento de sync).
    synced_to_authentik: Optional[bool] = None
    sync_error: Optional[str] = None

    model_config = {"from_attributes": True}
