"""Sector / industry peer lookup.

STEP 5 STATUS: STUB. Real peer fetching uses Screener.in and lands in step 6.
For step 5 the Valuation Agent receives `available=False` and degrades its
qualitative findings to current-vs-historical comparisons only.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from app.schemas.valuation import PeerComparison

log = structlog.get_logger(__name__)


class PeersService:
    async def fetch(self, ticker: str) -> PeerComparison:
        log.info(
            "peers.fetch.stub",
            ticker=ticker.upper(),
            note="Real peer scraper lands in step 6.",
        )
        return PeerComparison(
            available=False,
            peers=[],
            note="Peer comparison not yet implemented (step 6).",
            fetched_at=datetime.now(UTC),
        )
