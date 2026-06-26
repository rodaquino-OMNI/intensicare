"""Redis client initialization and utilities."""

import redis.asyncio as aioredis
from intensicare.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Get or create the Redis client (lazy init)."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
