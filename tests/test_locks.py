"""Unit tests for Redis research locks (fakeredis)."""

from __future__ import annotations

import fakeredis

from crypto_intel.redis.locks import (
    acquire_research_lock,
    release_research_lock,
    research_lock_key,
)


def test_acquire_and_release_research_lock() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    handle = acquire_research_lock(
        client,
        cryptocurrency="ETH",
        ttl_seconds=60,
    )
    assert handle is not None
    assert client.get(handle.key) == handle.token

    second = acquire_research_lock(
        client,
        cryptocurrency="ETH",
        ttl_seconds=60,
    )
    assert second is None

    release_research_lock(client, handle)
    assert client.get(research_lock_key("ETH")) is None

    third = acquire_research_lock(
        client,
        cryptocurrency="ETH",
        ttl_seconds=60,
    )
    assert third is not None
