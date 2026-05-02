"""Typed Redis cache for Pydantic models.

Generic over `BaseModel`: callers pass the model class on read so we can
validate the cached JSON back into a typed object instead of a `dict`.
"""

from __future__ import annotations

from typing import TypeVar

import redis.asyncio as redis_async
import structlog
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
log = structlog.get_logger(__name__)


class CacheService:
    def __init__(self, redis: redis_async.Redis) -> None:
        self._redis = redis

    @classmethod
    def from_url(cls, url: str) -> CacheService:
        # decode_responses=False so model_validate_json gets bytes — Pydantic
        # parses them directly without an extra decode step.
        return cls(redis_async.from_url(url, decode_responses=False))

    async def get(self, key: str, model: type[T]) -> T | None:
        raw = await self._redis.get(key)
        if raw is None:
            log.debug("cache.miss", key=key)
            return None
        log.debug("cache.hit", key=key)
        return model.model_validate_json(raw)

    async def set(self, key: str, value: BaseModel, ttl_seconds: int) -> None:
        await self._redis.set(key, value.model_dump_json(), ex=ttl_seconds)
        log.debug("cache.set", key=key, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> int:
        return int(await self._redis.delete(key))

    async def aclose(self) -> None:
        await self._redis.aclose()
