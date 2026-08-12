"""Redis client factory."""

from __future__ import annotations

from functools import lru_cache

import redis

from crypto_intel.settings import RedisSettings, get_settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    """Return a shared Redis client from settings.redis."""
    return build_redis(get_settings().redis)


def build_redis(settings: RedisSettings) -> redis.Redis:
    """Build a Redis client from a settings slice (tests inject fakeredis URL or client)."""
    return redis.Redis.from_url(settings.url, decode_responses=True)
