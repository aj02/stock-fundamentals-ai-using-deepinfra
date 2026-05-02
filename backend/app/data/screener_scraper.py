"""Polite, rate-limited Screener.in scraper.

Step 6 implementation. Behaviour:
  - Fetches /company/{ticker}/consolidated/ over the configured httpx client.
  - Sets a clear identifying User-Agent (see SCRAPER_USER_AGENT).
  - Acquires a per-host slot from the Redis-backed RedisRateLimiter
    (configured to 1 request / 3 s by default).
  - Caches the parsed snapshot for SCRAPER_TTL_SCREENER_SECONDS.
  - Parses HTML with selectolax (NOT BeautifulSoup, per stack constraints).
  - Extracts: company name (h1), Pros/Cons bullets (div.pros li / div.cons li),
    and Annual Report PDF links (anchors tagged with the
    `plausible-event-name=Annual+Report` class).
  - On any failure: logs, returns ScreenerSnapshot(available=False) so
    downstream agents continue with partial data — no crash.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog
from selectolax.parser import HTMLParser

from app.core.config import Settings
from app.data.rate_limiter import RedisRateLimiter
from app.schemas.financials import ScreenerAnnualReportLink, ScreenerSnapshot
from app.services.cache import CacheService

log = structlog.get_logger(__name__)

SCREENER_BASE_URL = "https://www.screener.in"


class ScreenerScraper:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        cache: CacheService,
        rate_limiter: RedisRateLimiter,
        settings: Settings,
    ) -> None:
        self._http = http_client
        self._cache = cache
        self._rate_limiter = rate_limiter
        self._settings = settings
        self._host = urlparse(SCREENER_BASE_URL).netloc

    async def fetch_company(self, ticker: str) -> ScreenerSnapshot:
        ticker_u = ticker.upper().replace(".NS", "").replace(".BO", "")
        cache_key = f"screener:company:{ticker_u}"

        cached = await self._cache.get(cache_key, ScreenerSnapshot)
        if cached is not None:
            log.debug("screener.cache_hit", ticker=ticker_u)
            return cached

        url = f"{SCREENER_BASE_URL}/company/{ticker_u}/consolidated/"

        try:
            await self._rate_limiter.acquire(self._host)
            log.info("screener.fetch.start", ticker=ticker_u, url=url)
            resp = await self._http.get(url, follow_redirects=True)
            if resp.status_code == 404:
                # Try the standalone (non-consolidated) URL as fallback —
                # smaller companies sometimes don't have a consolidated page.
                fallback = f"{SCREENER_BASE_URL}/company/{ticker_u}/"
                log.info("screener.fetch.consolidated_404_trying_standalone", url=fallback)
                resp = await self._http.get(fallback, follow_redirects=True)
                url = fallback
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001 — graceful-degrade is the point
            log.warning("screener.fetch.failed", ticker=ticker_u, error=str(exc))
            snap = ScreenerSnapshot(
                ticker=ticker_u,
                available=False,
                source_url=url,
                note=f"Fetch failed: {type(exc).__name__}",
                fetched_at=datetime.now(UTC),
            )
            await self._cache.set(
                cache_key, snap, ttl_seconds=300  # short TTL on failure so we retry sooner
            )
            return snap

        try:
            parsed = _parse_company_page(resp.text, ticker_u, url)
        except Exception as exc:  # noqa: BLE001
            log.warning("screener.parse.failed", ticker=ticker_u, error=str(exc))
            parsed = ScreenerSnapshot(
                ticker=ticker_u,
                available=False,
                source_url=url,
                note=f"Parse failed: {type(exc).__name__}",
                fetched_at=datetime.now(UTC),
            )

        await self._cache.set(
            cache_key, parsed, ttl_seconds=self._settings.CACHE_TTL_SCREENER_SECONDS
        )
        log.info(
            "screener.fetch.done",
            ticker=ticker_u,
            company_name=parsed.company_name,
            pros=len(parsed.pros),
            cons=len(parsed.cons),
            annual_reports=len(parsed.annual_reports),
        )
        return parsed


_FY_LABEL_RE = re.compile(r"financial\s+year\s+(\d{4})", re.IGNORECASE)


def _parse_company_page(html: str, ticker: str, source_url: str) -> ScreenerSnapshot:
    tree = HTMLParser(html)

    company_name: str | None = None
    h1 = tree.css_first("h1")
    if h1:
        company_name = h1.text(strip=True) or None

    pros: list[str] = []
    pros_div = tree.css_first("div.pros")
    if pros_div:
        for li in pros_div.css("li"):
            t = li.text(strip=True)
            if t:
                pros.append(t)

    cons: list[str] = []
    cons_div = tree.css_first("div.cons")
    if cons_div:
        for li in cons_div.css("li"):
            t = li.text(strip=True)
            if t:
                cons.append(t)

    annual_reports: list[ScreenerAnnualReportLink] = []
    # Class string Screener attaches: "plausible-event-name=Annual+Report ...".
    # We can't filter by attribute equality with selectolax CSS easily, so we
    # walk every <a> and check the class string ourselves.
    seen_urls: set[str] = set()
    for a in tree.css("a"):
        cls = a.attributes.get("class") or ""
        if "Annual+Report" not in cls and "Annual Report" not in cls:
            continue
        href = (a.attributes.get("href") or "").strip()
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        label = a.text(strip=True)
        fy_year = _extract_year(label)
        source = _guess_source(href, label)

        annual_reports.append(
            ScreenerAnnualReportLink(
                fiscal_year_label=label,
                fiscal_year=fy_year,
                source=source,
                url=href,
            )
        )

    # Keep only non-zip PDFs sorted newest-first (NSE sometimes hands ZIPs).
    annual_reports = [
        ar for ar in annual_reports if ar.url.lower().endswith(".pdf")
    ]
    annual_reports.sort(
        key=lambda ar: ar.fiscal_year if ar.fiscal_year is not None else 0,
        reverse=True,
    )

    return ScreenerSnapshot(
        ticker=ticker,
        available=True,
        company_name=company_name,
        pros=pros,
        cons=cons,
        annual_reports=annual_reports,
        source_url=source_url,
        note=None,
        fetched_at=datetime.now(UTC),
    )


def _extract_year(label: str) -> int | None:
    m = _FY_LABEL_RE.search(label)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _guess_source(url: str, label: str) -> Any:
    lower = (url + " " + label).lower()
    if "bseindia.com" in lower or "from bse" in lower:
        return "bse"
    if "nseindia.com" in lower or "from nse" in lower:
        return "nse"
    return "unknown"
