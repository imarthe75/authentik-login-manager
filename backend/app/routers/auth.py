import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.config import settings
from app.utils.session import SESSION_TTL_SECONDS, sign_session_token, verify_session_token
from app.routers.admin import (
    _admin_rate_limit_client_ip,
    _register_failed_admin_key_attempt,
)

log = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Admin Auth"])

SESSION_COOKIE_NAME = "admin_session"


class AdminLoginRequest(BaseModel):
    admin_key: str


@auth_router.post("/login")
async def login(payload: AdminLoginRequest, request: Request, response: Response):
    """Cambia ADMIN_API_KEY por una cookie de sesión HttpOnly — la clave nunca
    llega al navegador (a diferencia del VITE_ADMIN_KEY embebido que existía
    antes)."""
    client_ip = _admin_rate_limit_client_ip(request)

    if not secrets.compare_digest(payload.admin_key, settings.ADMIN_API_KEY):
        await _register_failed_admin_key_attempt(client_ip)
        log.warning("Invalid admin login attempt from IP %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials.",
        )

    token = sign_session_token(settings.SESSION_SECRET)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True}


@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"authenticated": False}


@auth_router.get("/status")
async def status_check(admin_session: Optional[str] = Cookie(None)):
    return {"authenticated": bool(admin_session and verify_session_token(admin_session, settings.SESSION_SECRET))}
