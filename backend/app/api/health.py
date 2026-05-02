"""Liveness + readiness endpoints.

`/health` is liveness-only — it MUST stay cheap so docker / k8s never wait
on a downstream when deciding whether to restart the process. `/ready` does
the heavier check that DB and Redis are actually reachable.

Both endpoints embed the `disclaimer` field that every API response in this
project is required to carry.
"""

from __future__ import annotations

from typing import Literal

import redis.asyncio as redis_async
import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import DISCLAIMER, get_settings
from app.core.db import SessionLocal

router = APIRouter(tags=["health"])
log = structlog.get_logger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    disclaimer: str = Field(default=DISCLAIMER)


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    postgres: Literal["ok", "error"]
    redis: Literal["ok", "error"]
    disclaimer: str = Field(default=DISCLAIMER)


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    settings = get_settings()

    postgres_status: Literal["ok", "error"] = "error"
    try:
        async with SessionLocal() as s:
            await s.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception as exc:  # noqa: BLE001
        log.warning("ready.postgres_check_failed", error=str(exc))

    redis_status: Literal["ok", "error"] = "error"
    client: redis_async.Redis | None = None
    try:
        client = redis_async.from_url(settings.REDIS_URL)
        if await client.ping():
            redis_status = "ok"
    except Exception as exc:  # noqa: BLE001
        log.warning("ready.redis_check_failed", error=str(exc))
    finally:
        if client is not None:
            await client.aclose()

    overall: Literal["ready", "degraded"] = (
        "ready" if postgres_status == "ok" and redis_status == "ok" else "degraded"
    )
    return ReadyResponse(status=overall, postgres=postgres_status, redis=redis_status)
