"""Ticker autocomplete endpoint.

Backed by a curated ~250-stock NSE universe (see app.data.tickers_seed).
Real-world deployment would back this with a NSE/BSE security master
refreshed nightly, but that's out of scope for the showcase.

Free-text input still works in the UI — yfinance validates the symbol
when the orchestrator runs, so users can type anything.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.core.config import DISCLAIMER
from app.data.tickers_seed import KNOWN_TICKERS_SEED

router = APIRouter(tags=["tickers"])


class TickerInfo(BaseModel):
    ticker: str
    name: str
    sector: str
    exchange: Literal["NSE", "BSE"] = "NSE"


class TickersSearchResponse(BaseModel):
    query: str
    results: list[TickerInfo]
    total_universe: int = Field(..., description="Total tickers in the curated universe.")
    disclaimer: str = Field(default=DISCLAIMER)


# Build the searchable list once at import time.
_UNIVERSE: list[TickerInfo] = [
    TickerInfo(ticker=row["ticker"], name=row["name"], sector=row["sector"])
    for row in KNOWN_TICKERS_SEED
]


@router.get(
    "/tickers/search",
    response_model=TickersSearchResponse,
    summary="Autocomplete a ticker against the curated NSE list (~250 stocks).",
)
async def search_tickers(
    q: str = Query("", description="Partial match on ticker or company name."),
    limit: int = Query(12, ge=1, le=50),
) -> TickersSearchResponse:
    qq = q.strip().upper()
    if not qq:
        # Show the most popular tickers when the query is empty.
        return TickersSearchResponse(
            query=q,
            results=_UNIVERSE[:limit],
            total_universe=len(_UNIVERSE),
        )

    # Three-tier match: ticker prefix → ticker substring → name substring.
    prefix = [t for t in _UNIVERSE if t.ticker.startswith(qq)]
    seen = {t.ticker for t in prefix}
    contains = [t for t in _UNIVERSE if t.ticker not in seen and qq in t.ticker]
    seen |= {t.ticker for t in contains}
    name = [t for t in _UNIVERSE if t.ticker not in seen and qq in t.name.upper()]

    combined = prefix + contains + name
    return TickersSearchResponse(
        query=q,
        results=combined[:limit],
        total_universe=len(_UNIVERSE),
    )
