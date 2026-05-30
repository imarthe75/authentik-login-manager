import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.cache import cache
from app.routers import admin, public

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Valkey connection
    logger.info("Initializing cache client...")
    cache.connect()
    
    # 2. Asynchronously verify database connection or run schema creations if necessary
    # (Note: In production we rely on Alembic, but we ensure DB availability here)
    logger.info("Verifying database connectivity...")
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        logger.info("Database connectivity established.")
        
    yield
    
    # 3. Cleanup connections
    logger.info("Shutting down cache client connection...")
    await cache.close()
    logger.info("FastAPI application stopped cleanly.")

app = FastAPI(
    title="Authentik Login Manager SaaS API",
    description="SaaS core REST API to visually design and persist dynamic portal themes for Authentik Flows.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration matching secure allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Key", "Authorization"],
)

# Include Routers
app.include_router(admin.router)
app.include_router(public.router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "cache": "connected" if cache.redis is not None else "disconnected"
    }
