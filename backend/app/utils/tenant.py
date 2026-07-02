import logging
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.tenant import Tenant
from app.cache import cache

logger = logging.getLogger(__name__)

# UUID del tenant por defecto (debe coincidir con la migración)
DEFAULT_TENANT_UUID = "00000000-0000-0000-0000-000000000001"


async def extract_tenant_id_from_domain(
    hostname: str,
    db: AsyncSession,
    use_cache: bool = True
) -> str:
    """
    Resuelve un hostname a un tenant_id buscando coincidencia de dominio.

    Estrategia:
    1. Extraer dominio base de hostname (ej: "casmarts.local" de "portal.casmarts.local")
    2. Buscar en caché Redis
    3. Si no está en caché, buscar en DB (comparar con domain_pattern)
    4. Guardar en caché (TTL 1 hora)
    5. Si no hay coincidencia, usar tenant por defecto

    Args:
        hostname: ej "portal.casmarts.local", "brand2.sample", "localhost"
        db: sesión de BD
        use_cache: si usar Redis para caché

    Returns:
        UUID del tenant encontrado o DEFAULT_TENANT_UUID
    """

    # Normalizar hostname
    hostname = hostname.lower().strip()
    if hostname.startswith("http://") or hostname.startswith("https://"):
        # Si viene como URL, extraer solo el host
        hostname = hostname.split("://")[1].split("/")[0]

    # Intentar caché primero
    if use_cache:
        cache_key = f"tenant:domain:{hostname}"
        cached_tenant_id = await cache.get(cache_key)
        if cached_tenant_id:
            logger.info(f"Cache hit for hostname '{hostname}' → tenant {cached_tenant_id}")
            return cached_tenant_id

    # Buscar en BD
    result = await db.execute(
        select(Tenant)
        .where(Tenant.is_active == True)
        .order_by(Tenant.created_at.asc())
    )
    tenants = result.scalars().all()

    matched_tenant_id = None

    for tenant in tenants:
        if _matches_domain_pattern(hostname, tenant.domain_pattern):
            matched_tenant_id = str(tenant.id)
            logger.info(f"Domain '{hostname}' matched pattern '{tenant.domain_pattern}' → tenant {matched_tenant_id}")
            break

    # Si no hay coincidencia, usar por defecto
    if not matched_tenant_id:
        matched_tenant_id = DEFAULT_TENANT_UUID
        logger.warning(
            f"Hostname '{hostname}' no coincidió con ningún pattern. "
            f"Usando tenant por defecto: {DEFAULT_TENANT_UUID}"
        )

    # Guardar en caché (TTL 1 hora = 3600s)
    if use_cache and cache.redis:
        try:
            await cache.set(f"tenant:domain:{hostname}", matched_tenant_id, ex=3600)
        except Exception as e:
            logger.error(f"Error guardando en caché: {e}")

    return matched_tenant_id


def _matches_domain_pattern(hostname: str, pattern: str) -> bool:
    """
    Verifica si un hostname coincide con un patrón de dominio.

    Soporta:
    - Exact match: "casmarts.local" == "casmarts.local"
    - Wildcard: "*.casmarts.local" coincide con "portal.casmarts.local", "api.casmarts.local"
    - Regex: Soporta patrones como "brand[0-9]\.local"

    Args:
        hostname: "portal.casmarts.local"
        pattern: "casmarts.local" o "*.casmarts.local" o "brand[0-9]\.local"

    Returns:
        True si coincide, False si no
    """

    # Case-insensitive
    hostname = hostname.lower()
    pattern = pattern.lower()

    # Exact match
    if hostname == pattern:
        return True

    # Wildcard pattern: "*.domain.com"
    if pattern.startswith("*."):
        domain_part = pattern[2:]
        if hostname.endswith("." + domain_part):
            return True
        # También coincide si es el dominio exacto (sin subdominio)
        if hostname == domain_part:
            return True

    # Regex pattern (si contiene caracteres especiales regex)
    if any(c in pattern for c in "[]()?+^$|\\"):
        try:
            if re.match(f"^{pattern}$", hostname):
                return True
        except re.error as e:
            logger.error(f"Error en regex pattern '{pattern}': {e}")

    return False


async def get_tenant_or_default(
    hostname: Optional[str],
    db: AsyncSession
) -> Optional[Tenant]:
    """
    Obtiene el tenant basado en hostname, o el tenant por defecto.

    Args:
        hostname: ej "portal.casmarts.local" o None
        db: sesión de BD

    Returns:
        Objeto Tenant o None si no existe
    """

    if not hostname:
        # Obtener tenant por defecto
        result = await db.execute(
            select(Tenant).where(Tenant.id == DEFAULT_TENANT_UUID)
        )
        return result.scalar_one_or_none()

    tenant_id = await extract_tenant_id_from_domain(hostname, db)

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    return result.scalar_one_or_none()


async def invalidate_tenant_cache(hostname: str) -> None:
    """
    Invalida la entrada de caché para un hostname.
    Útil después de crear/actualizar un tenant.
    """

    cache_key = f"tenant:domain:{hostname.lower()}"
    try:
        await cache.delete(cache_key)
        logger.info(f"Cache invalidado para hostname '{hostname}'")
    except Exception as e:
        logger.error(f"Error invalidando caché: {e}")
