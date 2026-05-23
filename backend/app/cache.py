"""Fail-soft Redis cache for expensive aggregation responses.

The Cache wrapper deliberately swallows every Redis error: a cache miss and
a Redis outage are indistinguishable from the caller's perspective, so the
endpoints stay available even when Redis is down. Aggregations are
invalidated explicitly after a batch recompute; TTL guards everything else.
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import Redis

from app.config import settings

log = logging.getLogger(__name__)

# Every cache key produced by this module starts with this prefix so
# ``invalidate_all`` can wipe them without touching anything else in Redis.
KEY_PREFIX = "agg:"


class Cache:
    """Thin wrapper around an ``redis.asyncio.Redis`` client."""

    def __init__(self, redis: Redis | None, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    async def get_json(self, key: str) -> Any | None:
        """Return the cached JSON-decoded value, or ``None`` on miss/outage."""
        if not self._redis:
            return None
        try:
            raw = await self._redis.get(KEY_PREFIX + key)
        except Exception:
            log.warning("cache GET failed for %s", key, exc_info=True)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        """Best-effort write. Connection errors are logged and swallowed."""
        if not self._redis:
            return
        try:
            payload = json.dumps(value, default=str, ensure_ascii=False)
            await self._redis.set(
                KEY_PREFIX + key, payload, ex=ttl if ttl is not None else self._ttl
            )
        except Exception:
            log.warning("cache SET failed for %s", key, exc_info=True)

    async def invalidate_all(self) -> int:
        """Delete every key under our prefix. Returns the deletion count."""
        if not self._redis:
            return 0
        try:
            keys: list[str] = []
            async for k in self._redis.scan_iter(match=KEY_PREFIX + "*"):
                keys.append(k)
            if not keys:
                return 0
            return int(await self._redis.delete(*keys))
        except Exception:
            log.warning("cache invalidate failed", exc_info=True)
            return 0


# A single Redis client is shared across requests so the connection pool stays
# warm. Construction is lazy so tests can override the dependency before the
# pool is created against an unreachable Redis.
_shared_client: Redis | None = None


def _get_shared_client() -> Redis | None:
    global _shared_client
    if _shared_client is not None:
        return _shared_client
    try:
        _shared_client = Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        log.warning("failed to build Redis client", exc_info=True)
        _shared_client = None
    return _shared_client


async def get_cache() -> AsyncIterator[Cache]:
    """FastAPI dependency yielding a fail-soft ``Cache``."""
    yield Cache(redis=_get_shared_client(), ttl_seconds=settings.cache_ttl_seconds)
