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
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
