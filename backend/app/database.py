import socket
from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Create asynchronous engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=30,
    pool_use_lifo=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

def _request_client_ip(request: Request) -> str:
    # Mismo criterio que _admin_rate_limit_client_ip en routers/admin.py:
    # request.client.host es la IP del gateway, no la del navegador real,
    # salvo que la conexión TCP venga del propio gateway de confianza.
    client_ip = request.client.host if request.client else "unknown"
    trusted_host = getattr(settings, "TRUSTED_PROXY_HOST", None) or "casmarts-core-gateway"
    try:
        trusted = socket.gethostbyname(trusted_host)
    except socket.gaierror:
        trusted = None
    if request.client and (trusted is None or request.client.host == trusted):
        client_ip = request.headers.get("X-Real-IP", client_ip)
    return client_ip


# Dependency to get async database session
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            # Estandar de auditoria CASMART (postgres/rules.md #4.1): sin esto,
            # el trigger audit_biu registra el usuario_modificacion con el rol
            # tecnico de conexion para TODO cambio, de cualquier tenant, sin
            # distinguir quien lo hizo. Este backend no tiene cuentas por
            # persona (una sola ADMIN_API_KEY compartida por tenant) — la
            # mejor atribucion disponible es la IP de origen de la peticion.
            # is_local=true (3er argumento) para que no se filtre a otra
            # peticion si el pool reutiliza la conexion.
            usuario = f"login_manager_admin:{_request_client_ip(request)}"
            await session.execute(text("SELECT set_config('app.current_user', :u, true)"), {"u": usuario})
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
