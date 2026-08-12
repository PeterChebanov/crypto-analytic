"""Redis distributed locks for research runs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

import redis


@dataclass(frozen=True, slots=True)
class LockHandle:
    key: str
    token: str


def research_lock_key(cryptocurrency: str, day: date | None = None) -> str:
    locked_day = day or date.today()
    symbol = cryptocurrency.strip().upper()
    return f"research:{symbol}:{locked_day.isoformat()}"


def acquire_research_lock(
    client: redis.Redis,
    *,
    cryptocurrency: str,
    ttl_seconds: int,
    day: date | None = None,
) -> LockHandle | None:
    """Acquire a short-lived NX lock. Returns None if already held."""
    key = research_lock_key(cryptocurrency, day=day)
    token = uuid.uuid4().hex
    acquired = client.set(key, token, nx=True, ex=ttl_seconds)
    if not acquired:
        return None
    return LockHandle(key=key, token=token)


def release_research_lock(client: redis.Redis, handle: LockHandle) -> None:
    """Release lock only if token still matches (safe unlock)."""
    current = client.get(handle.key)
    if current == handle.token:
        client.delete(handle.key)
