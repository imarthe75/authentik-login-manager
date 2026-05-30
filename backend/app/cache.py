import logging
import json
from typing import Optional, Any
import redis.asyncio as aioredis
from app.config import settings

class CacheClient:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    def connect(self):
        try:
            self.redis = aioredis.Redis.from_url(
                settings.VALKEY_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
            logging.info("Valkey cache connection pool established.")
        except Exception as e:
            logging.error(f"Failed to connect to Valkey cache: {e}")
            self.redis = None

    async def get(self, key: str) -> Optional[str]:
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logging.error(f"Valkey GET error: {e}")
            return None

    async def set(self, key: str, value: str, ex: int = 300) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.set(key, value, ex=ex)
            return True
        except Exception as e:
            logging.error(f"Valkey SET error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logging.error(f"Valkey DELETE error: {e}")
            return False

    async def close(self):
        if self.redis:
            await self.redis.close()
            logging.info("Valkey cache connection pool closed.")

cache = CacheClient()
