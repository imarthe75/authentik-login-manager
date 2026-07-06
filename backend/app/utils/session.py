"""Firma/verificación de sesión de admin sin dependencias nuevas (stdlib only).

Reemplaza el modelo anterior de "clave estática embebida en el bundle del
cliente" (VITE_ADMIN_KEY) por una cookie de sesión HttpOnly emitida tras un
login explícito con ADMIN_API_KEY. El secreto de firma (SESSION_SECRET) nunca
sale del backend, a diferencia de ADMIN_API_KEY que hasta ahora viajaba en el
JS servido al navegador.
"""
import hmac
import hashlib
import time
from typing import Optional

SESSION_TTL_SECONDS = 8 * 3600  # 8 horas


def sign_session_token(secret: str) -> str:
    issued_at = str(int(time.time()))
    signature = hmac.new(secret.encode(), issued_at.encode(), hashlib.sha256).hexdigest()
    return f"{issued_at}.{signature}"


def verify_session_token(token: Optional[str], secret: str) -> bool:
    if not token or "." not in token:
        return False
    issued_at_str, _, signature = token.partition(".")
    try:
        issued_at = int(issued_at_str)
    except ValueError:
        return False
    expected = hmac.new(secret.encode(), issued_at_str.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    return (time.time() - issued_at) <= SESSION_TTL_SECONDS
