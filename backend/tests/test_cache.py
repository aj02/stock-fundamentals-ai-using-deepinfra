"""Cache roundtrip test against a real Redis.

Skipped automatically if REDIS_URL is unreachable so a developer running
`pytest` without docker-compose up doesn't see a confusing failure.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
import redis.asyncio as redis_async

from app.schemas.financials import ScreenerSnapshot
from app.services.cache import CacheService


@pytest.fixture
async def cache() -> CacheService:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    client = redis_async.from_url(redis_url, decode_responses=False)
    try:
        await client.ping()
    except Exception:
        pytest.skip(f"Redis unreachable at {redis_url}")
    yield CacheService(client)
    await client.aclose()


async def test_cache_roundtrip_pydantic_model(cache: CacheService) -> None:
    key = "test:screener:cache_roundtrip"
    original = ScreenerSnapshot(
        ticker="TESTCO",
        available=False,
        note="roundtrip",
        fetched_at=datetime.now(UTC),
    )

    await cache.set(key, original, ttl_seconds=60)
    loaded = await cache.get(key, ScreenerSnapshot)

    assert loaded is not None
    assert loaded.ticker == "TESTCO"
    assert loaded.note == "roundtrip"
    # Datetime survives JSON roundtrip.
    assert loaded.fetched_at.replace(microsecond=0) == original.fetched_at.replace(microsecond=0)

    deleted = await cache.delete(key)
    assert deleted == 1

    after_delete = await cache.get(key, ScreenerSnapshot)
    assert after_delete is None


async def test_cache_miss_returns_none(cache: CacheService) -> None:
    assert await cache.get("test:does_not_exist:xyz", ScreenerSnapshot) is None
