import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


class RedisCache:
    def __init__(self, prefix: str = "", default_ttl: int = 300):
        self.prefix = prefix
        self.default_ttl = default_ttl

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}" if self.prefix else key

    async def get(self, key: str) -> Any | None:
        redis = await get_redis()
        value = await redis.get(self._key(key))
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        redis = await get_redis()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await redis.set(self._key(key), serialized, ex=ttl or self.default_ttl)

    async def delete(self, key: str) -> None:
        redis = await get_redis()
        await redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        redis = await get_redis()
        return bool(await redis.exists(self._key(key)))

    async def invalidate_pattern(self, pattern: str) -> None:
        redis = await get_redis()
        keys = await redis.keys(self._key(pattern))
        if keys:
            await redis.delete(*keys)
