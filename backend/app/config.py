import os
import secrets
import logging
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str
    VALKEY_URL: str
    ADMIN_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"
    # Hostname Docker del gateway/reverse-proxy confiable: solo se aceptan los
    # headers X-Tenant-Domain/X-Forwarded-Host si la conexión TCP proviene de
    # este host (ver _is_trusted_proxy_peer en routers/admin.py).
    TRUSTED_PROXY_HOST: str = "casmarts-core-gateway"
    # SMTP para envío de correos de prueba
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ADMIN_API_KEY", mode="after")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v:
            # Fallback securely as defined by mandatory-secure-web-skills guidelines:
            logging.warning("Generating ephemeral ADMIN_API_KEY. Instance-isolated!")
            return secrets.token_hex(32)
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if "*" in origins:
            # allow_credentials=True + wildcard origin is an invalid/dangerous CORS
            # combination (any site could make authenticated cross-origin requests).
            # Fail closed to the safe default rather than deploy silently insecure.
            logging.error(
                "CORS_ORIGINS contains '*' with allow_credentials=True — refusing to "
                "use wildcard. Falling back to localhost-only origins. Set explicit "
                "origins in CORS_ORIGINS."
            )
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return origins

settings = Settings()
