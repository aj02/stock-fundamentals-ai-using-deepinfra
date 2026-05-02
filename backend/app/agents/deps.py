"""Shared dependency container for every PydanticAI agent.

PydanticAI passes a single `deps` object into every tool's `RunContext`. We
keep that object slim and ALL services reachable through it, so a tool only
needs `ctx.deps.<service>` to act. The factory returns the deps alongside
an `AsyncExitStack` that owns the cleanup of any external resources (HTTP
client, Redis connection) — callers `await stack.aclose()` when done.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings
from app.data.annual_report import AnnualReportService
from app.data.peers import PeersService
from app.data.rate_limiter import RedisRateLimiter
from app.data.screener_scraper import ScreenerScraper
from app.data.yfinance_client import YFinanceClient
from app.services.cache import CacheService


@dataclass(slots=True)
class AgentDeps:
    settings: Settings
    cache: CacheService
    yfinance_client: YFinanceClient
    screener_scraper: ScreenerScraper
    peers_service: PeersService
    annual_report_service: AnnualReportService


async def build_agent_deps() -> tuple[AgentDeps, AsyncExitStack]:
    settings = get_settings()
    stack = AsyncExitStack()

    cache = CacheService.from_url(settings.REDIS_URL)
    stack.push_async_callback(cache.aclose)

    http_client = httpx.AsyncClient(
        headers={"User-Agent": settings.SCRAPER_USER_AGENT},
        timeout=httpx.Timeout(20.0, connect=10.0),
    )
    stack.push_async_callback(http_client.aclose)

    rate_limiter = RedisRateLimiter(
        redis=cache._redis,  # noqa: SLF001  — intentional internal access for sharing the connection
        namespace="screener",
        min_interval_seconds=settings.SCRAPER_MIN_INTERVAL_SECONDS,
    )

    yfinance_client = YFinanceClient(cache=cache, settings=settings)
    screener_scraper = ScreenerScraper(
        http_client=http_client,
        cache=cache,
        rate_limiter=rate_limiter,
        settings=settings,
    )

    peers_service = PeersService()

    # Annual reports are large; share the same rate-limiter for the BSE/NSE
    # PDF hosts so we stay polite there too.
    ar_download_limiter = RedisRateLimiter(
        redis=cache._redis,  # noqa: SLF001
        namespace="ar_download",
        min_interval_seconds=settings.SCRAPER_MIN_INTERVAL_SECONDS,
    )
    annual_report_service = AnnualReportService(
        http_client=http_client,
        cache=cache,
        screener_scraper=screener_scraper,
        settings=settings,
        rate_limiter=ar_download_limiter,
    )

    deps = AgentDeps(
        settings=settings,
        cache=cache,
        yfinance_client=yfinance_client,
        screener_scraper=screener_scraper,
        peers_service=peers_service,
        annual_report_service=annual_report_service,
    )
    return deps, stack
