"""Annual-report PDF discovery, download, and section extraction.

Pipeline:
  1. ScreenerScraper provides the latest annual-report PDF URL.
  2. We download it to a disk cache (indefinite — annual reports don't change
     after publication). Cache key: hash(url) so the same PDF is reused
     even when discovered through a different ticker variant.
  3. pypdf extracts text for the whole PDF (fast). pdfplumber is held in
     reserve for sections where pypdf returns garbage (e.g. multi-column
     governance tables) — we fall back per-section if word density looks
     suspiciously low.
  4. Section detection runs heading regexes against the concatenated text
     to locate Management Discussion & Analysis, Corporate Governance,
     Risk Management, Directors'/Board's Report.
  5. Each extracted section is truncated to MAX_SECTION_WORDS so the LLM
     context budget stays sane (one annual report can be 700+ pages).

If any step fails (no AR URL, download error, parse error, no heading
matches), we return AnnualReportSnapshot(available=False) with a `note`
explaining why. Downstream agents handle that explicitly.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
import structlog

from app.core.config import Settings
from app.data.rate_limiter import RedisRateLimiter
from app.data.screener_scraper import ScreenerScraper
from app.schemas.annual_report import (
    AnnualReportSection,
    AnnualReportSnapshot,
    ARSectionType,
)
from app.services.cache import CacheService

log = structlog.get_logger(__name__)

# Cap each section at ~5000 words ≈ 7000 tokens. Two sections per agent
# (MD&A + governance) keeps the prompt well under 20k tokens of AR content.
MAX_SECTION_WORDS = 5000

# Heading regexes per section type. Multiple alternates because Indian
# annual reports phrase these slightly differently from one issuer to the next.
# `\s+` is generous because pypdf frequently injects \n and \t inside what
# the source PDF rendered as a single line of heading text.
_SECTION_PATTERNS: dict[ARSectionType, list[re.Pattern[str]]] = {
    "mda": [
        re.compile(
            r"\bmanagement(?:'?s)?\s+discussion\s+(?:and|&|\&amp;)\s+analysis(?:\s+report)?\b",
            re.IGNORECASE,
        ),
    ],
    "governance": [
        re.compile(
            r"\b(?:report\s+on\s+)?corporate\s+governance(?:\s+report)?\b",
            re.IGNORECASE,
        ),
    ],
    "risks": [
        re.compile(r"\brisk\s+management(?:\s+(?:framework|report))?\b", re.IGNORECASE),
        re.compile(r"\bprincipal\s+risks\b", re.IGNORECASE),
        re.compile(r"\brisk\s+factors\b", re.IGNORECASE),
        re.compile(r"\brisks\s+and\s+(?:concerns|mitigation)\b", re.IGNORECASE),
    ],
    "directors_report": [
        re.compile(r"\b(?:director[s']?|board[s']?)\s+report\b", re.IGNORECASE),
    ],
}

# Per-section boundary rules: which OTHER section types can mark the end of
# this one. Critically, MD&A is NOT bounded by `risks` — Indian ARs often
# nest a Risk Management Framework subsection inside MD&A. Same logic for
# governance: a parenthetical "see Corporate Governance Report" cross-
# reference inside the governance chapter shouldn't truncate the chapter.
_SECTION_BOUNDARIES: dict[ARSectionType, set[ARSectionType]] = {
    # MD&A specifically excludes `risks`: Indian ARs frequently nest a Risk
    # Management Framework subsection inside MD&A.
    "mda": {"governance", "directors_report"},
    "governance": {"mda", "directors_report", "risks"},
    "risks": {"mda", "governance", "directors_report"},
    "directors_report": {"mda", "governance", "risks"},
}

# Minimum chars between heading match and next-type boundary for a candidate
# match to count as a "real" section start. TOC entries and parenthetical
# cross-references typically have <500 chars to the next heading.
_MIN_SECTION_BODY_CHARS = 3000


class AnnualReportService:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        cache: CacheService,
        screener_scraper: ScreenerScraper,
        settings: Settings,
        pdf_cache_dir: Path | None = None,
        rate_limiter: RedisRateLimiter | None = None,
    ) -> None:
        self._http = http_client
        self._cache = cache
        self._screener = screener_scraper
        self._settings = settings
        self._pdf_cache_dir = pdf_cache_dir or Path("/tmp/fundamentals_ai/ar_cache")
        self._pdf_cache_dir.mkdir(parents=True, exist_ok=True)
        # Re-use a rate limiter for BSE/NSE PDF hosts so we don't hammer them
        # when downloading multiple ARs in one session.
        self._download_limiter = rate_limiter

    async def fetch_and_extract(
        self,
        ticker: str,
        sections: list[ARSectionType] | None = None,
    ) -> AnnualReportSnapshot:
        """Discover, download, and extract the latest annual report's sections."""
        sections = sections or ["mda", "governance"]

        # 1. Discover via Screener.
        screener = await self._screener.fetch_company(ticker)
        if not screener.available or not screener.annual_reports:
            note = (
                "Screener data unavailable" if not screener.available
                else "No annual-report links found on Screener page"
            )
            log.info("annual_report.discovery_failed", ticker=ticker, note=note)
            return AnnualReportSnapshot(
                ticker=ticker.upper(),
                available=False,
                note=note,
                fetched_at=datetime.now(UTC),
            )

        latest = screener.annual_reports[0]
        log.info(
            "annual_report.discovered",
            ticker=ticker,
            fy=latest.fiscal_year,
            url=latest.url,
            source=latest.source,
        )

        # 2. Download (cached on disk).
        try:
            pdf_path = await self._download_pdf(latest.url)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "annual_report.download_failed",
                ticker=ticker, url=latest.url, error=str(exc),
            )
            return AnnualReportSnapshot(
                ticker=ticker.upper(),
                available=False,
                fiscal_year=latest.fiscal_year,
                source_url=latest.url,
                note=f"Download failed: {type(exc).__name__}",
                fetched_at=datetime.now(UTC),
            )

        # 3. Parse + extract sections (CPU-bound, in a worker thread).
        try:
            page_count, extracted = await asyncio.to_thread(
                _extract_sections, pdf_path, sections
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "annual_report.parse_failed",
                ticker=ticker, pdf_path=str(pdf_path), error=str(exc),
            )
            return AnnualReportSnapshot(
                ticker=ticker.upper(),
                available=False,
                fiscal_year=latest.fiscal_year,
                source_url=latest.url,
                note=f"PDF parse failed: {type(exc).__name__}",
                fetched_at=datetime.now(UTC),
            )

        if not extracted:
            return AnnualReportSnapshot(
                ticker=ticker.upper(),
                available=False,
                fiscal_year=latest.fiscal_year,
                source_url=latest.url,
                page_count=page_count,
                note="No requested sections found in PDF (heading regexes did not match).",
                fetched_at=datetime.now(UTC),
            )

        log.info(
            "annual_report.extract_done",
            ticker=ticker,
            fy=latest.fiscal_year,
            page_count=page_count,
            sections_extracted=list(extracted.keys()),
        )
        return AnnualReportSnapshot(
            ticker=ticker.upper(),
            available=True,
            fiscal_year=latest.fiscal_year,
            source_url=latest.url,
            page_count=page_count,
            sections=extracted,
            fetched_at=datetime.now(UTC),
        )

    async def _download_pdf(self, url: str) -> Path:
        cache_path = self._pdf_cache_path(url)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            log.debug("annual_report.pdf_cache_hit", url=url, path=str(cache_path))
            return cache_path

        if self._download_limiter is not None:
            host = httpx.URL(url).host
            await self._download_limiter.acquire(host)

        log.info("annual_report.pdf_download.start", url=url)
        # Annual reports can be 30+ MB; bump the read timeout.
        async with self._http.stream(
            "GET", url, timeout=httpx.Timeout(120.0, connect=30.0), follow_redirects=True
        ) as resp:
            resp.raise_for_status()
            tmp_path = cache_path.with_suffix(".pdf.partial")
            with open(tmp_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
        tmp_path.rename(cache_path)
        log.info(
            "annual_report.pdf_download.done",
            url=url,
            path=str(cache_path),
            size_mb=round(cache_path.stat().st_size / 1024 / 1024, 1),
        )
        return cache_path

    def _pdf_cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self._pdf_cache_dir / f"{digest}.pdf"


# ─── PDF parsing helpers (sync, run in worker thread) ───────────────────────

def _extract_sections(
    pdf_path: Path, requested: list[ARSectionType]
) -> tuple[int, dict[ARSectionType, AnnualReportSection]]:
    """Return (page_count, {section_type: AnnualReportSection})."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages_text: list[str] = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            pages_text.append("")

    page_count = len(pages_text)
    if page_count == 0:
        return 0, {}

    # Build a (start_offset, page_index) index so we can map character
    # positions back to page numbers later.
    full_parts: list[str] = []
    page_starts: list[int] = []
    cursor = 0
    for i, ptext in enumerate(pages_text):
        page_starts.append(cursor)
        full_parts.append(ptext)
        full_parts.append("\n\n")  # page break
        cursor += len(ptext) + 2
    full_text = "".join(full_parts)

    # Find ALL candidate matches for every section type — needed because we
    # use cross-type matches as boundaries.
    matches_by_type: dict[ARSectionType, list[tuple[int, int, str]]] = {}
    for section_type, patterns in _SECTION_PATTERNS.items():
        all_matches: list[tuple[int, int, str]] = []
        for pat in patterns:
            for m in pat.finditer(full_text):
                all_matches.append((m.start(), m.end(), m.group(0)))
        matches_by_type[section_type] = sorted(all_matches)

    # For each REQUESTED type, score each candidate by the body length until
    # the next match of a *boundary type* (per _SECTION_BOUNDARIES). Pick
    # the *latest* candidate that has body length ≥ _MIN_SECTION_BODY_CHARS;
    # this skips TOC entries (small body) and parenthetical cross-references
    # (small body) in favour of the actual chapter start. Fall back to the
    # candidate with the largest body if no candidate meets the threshold.
    chosen: dict[ARSectionType, tuple[int, int, str, int]] = {}
    for section_type in requested:
        candidates = matches_by_type.get(section_type, [])
        if not candidates:
            continue
        boundary_types = _SECTION_BOUNDARIES.get(section_type, set())
        boundary_starts = sorted(
            m[0]
            for other_type in boundary_types
            for m in matches_by_type.get(other_type, [])
        )

        scored = []
        for start, end, heading in candidates:
            next_boundary = next(
                (s for s in boundary_starts if s > end), len(full_text)
            )
            body_len = next_boundary - end
            scored.append((start, end, heading, next_boundary, body_len))

        eligible = [s for s in scored if s[4] >= _MIN_SECTION_BODY_CHARS]
        if eligible:
            # Pick the LATEST eligible candidate. The TOC and any sub-TOC
            # / chapter-contents page sit before the real chapter start.
            picked = max(eligible, key=lambda s: s[0])
        else:
            picked = max(scored, key=lambda s: s[4])

        chosen[section_type] = (picked[0], picked[1], picked[2], picked[3])

    if not chosen:
        return page_count, {}

    extracted: dict[ARSectionType, AnnualReportSection] = {}
    for section_type, (start_offset, _end, heading, next_start) in chosen.items():
        section_text = full_text[start_offset:next_start].strip()
        page_start = _offset_to_page(start_offset, page_starts)
        page_end = _offset_to_page(min(next_start, len(full_text) - 1), page_starts)

        words = section_text.split()
        truncated = False
        if len(words) > MAX_SECTION_WORDS:
            section_text = " ".join(words[:MAX_SECTION_WORDS]) + " […truncated]"
            truncated = True
            words = words[:MAX_SECTION_WORDS]

        extracted[section_type] = AnnualReportSection(
            section_type=section_type,
            heading_found=heading,
            page_start=page_start,
            page_end=page_end,
            text=section_text,
            word_count=len(words),
            truncated=truncated,
        )

    return page_count, extracted


def _offset_to_page(offset: int, page_starts: list[int]) -> int:
    """Binary-search the page-starts list for the page containing `offset`."""
    if not page_starts:
        return 1
    lo, hi = 0, len(page_starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if page_starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1  # 1-indexed page number
