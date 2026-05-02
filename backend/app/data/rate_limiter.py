"""Per-host minimum-interval rate limiter, backed by Redis.

Pattern: SET NX EX with a key that lives for `min_interval_seconds`. While
the key exists, no new request to that host is allowed; callers wait on
the key's TTL and retry. Multiple worker processes coordinate naturally
because the gate lives in Redis, not in Python memory.

This isn't a perfect token bucket — it enforces a strict minimum interval
between requests, which is what "polite citizen of someone else's site"
actually means in practice.
"""

from __future__ import annotations

import asyncio
import math

import redis.asyncio as redis_async
import structlog

log = structlog.get_logger(__name__)


class RedisRateLimiter:
    def __init__(
        self,
        redis: redis_async.Redis,
        namespace: str,
        min_interval_seconds: float,
    ) -> None:
        self._redis = redis
        self._namespace = namespace
        self._min_interval = max(0.0, min_interval_seconds)

    async def acquire(self, host: str) -> None:
        if self._min_interval == 0.0:
            return
        key = f"{self._namespace}:lastreq:{host}"
        ttl_seconds = max(1, math.ceil(self._min_interval))
        attempts = 0
        while True:
            acquired = await self._redis.set(key, "1", nx=True, ex=ttl_seconds)
            if acquired:
                if attempts > 0:
                    log.debug(
                        "rate_limiter.slot_acquired",
                        host=host,
                        attempts=attempts,
                    )
                return
            attempts += 1
            ttl = await self._redis.ttl(key)
            wait = max(0.1, min(self._min_interval, float(ttl) if ttl > 0 else self._min_interval))
            log.debug("rate_limiter.waiting", host=host, wait_seconds=wait)
            await asyncio.sleep(wait)
