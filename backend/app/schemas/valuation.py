"""Pydantic schemas for the Valuation Agent.

Same evidence-discipline as `schemas.agents`: every qualitative finding
must reference at least one EvidenceLink with metric/years/values, claims
are length-bounded, and the agent must produce 4-7 findings.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DISCLAIMER
from app.schemas.agents import QualitativeFinding


class ValuationMultiples(BaseModel):
    """Current valuation multiples from yfinance .info."""

    model_config = ConfigDict(frozen=True)

    current_price: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    price_to_sales_ttm: float | None = None
    ev_to_ebitda: float | None = None
    ev_to_revenue: float | None = None
    dividend_yield_pct: float | None = None
    payout_ratio_pct: float | None = None
    book_value_per_share: float | None = None
    trailing_eps: float | None = None
    forward_eps: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    fetched_at: datetime


class HistoricalValuationPoint(BaseModel):
    """One fiscal year's snapshot of price × per-share fundamentals."""

    model_config = ConfigDict(frozen=True)

    period_end: date
    fy_end_close_price: float | None = None
    eps_for_year: float | None = None
    book_value_per_share: float | None = None
    pe: float | None = None
    pb: float | None = None


class HistoricalMedians(BaseModel):
    """Median multiples across the available history (newest-first)."""

    model_config = ConfigDict(frozen=True)

    pe_median: float | None = None
    pb_median: float | None = None
    pe_min: float | None = None
    pe_max: float | None = None
    pb_min: float | None = None
    pb_max: float | None = None
    years_in_window: int = 0


class HistoricalValuation(BaseModel):
    """Full historical valuation series + medians."""

    model_config = ConfigDict(frozen=True)

    yearly: list[HistoricalValuationPoint] = Field(default_factory=list)
    medians: HistoricalMedians


class PeerCompany(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str | None = None
    market_cap: float | None = None
    pe: float | None = None
    pb: float | None = None


class PeerComparison(BaseModel):
    """STEP 5 STATUS: STUB.

    Real peer lookup ships with the Screener.in scraper in step 6. Until
    then this returns `available=False` so the report builder + Valuation
    Agent exercise the missing-section path explicitly rather than
    silently skipping the comparison.
    """

    model_config = ConfigDict(frozen=True)

    available: bool = False
    peers: list[PeerCompany] = Field(default_factory=list)
    peer_pe_median: float | None = None
    peer_pb_median: float | None = None
    note: str = "Peer comparison not yet implemented (step 6)."
    fetched_at: datetime


class ValuationReport(BaseModel):
    """Output of the Valuation Agent."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    yfinance_symbol: str
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str = "INR"
    period_summary: str = Field(
        ...,
        description="Human-readable history window, e.g. 'FY2023 to FY2026 (4 years)'.",
    )
    current_multiples: ValuationMultiples
    historical_valuation: HistoricalValuation
    peer_comparison: PeerComparison
    qualitative_assessment: list[QualitativeFinding] = Field(
        ...,
        min_length=4,
        max_length=7,
        description=(
            "4-7 evidence-linked findings. MUST cover at least three of "
            "{current vs historical, P/E trajectory, P/B trajectory, "
            "dividend policy, EV/EBITDA, peer comparison if available}. "
            "DESCRIPTIVE only — no buy/sell/hold language, no 'fair value' or "
            "price target, no 'undervalued/overvalued' verdict (only "
            "factual statements like 'P/E is X% above the 5-year median')."
        ),
    )
    data_quality_notes: list[str] = Field(default_factory=list)
    generated_at: datetime
    disclaimer: str = Field(default=DISCLAIMER)


# Public re-export so the agent module doesn't reach into schemas.agents.
ValuationFindingCategory = Literal[
    "current_vs_history",
    "pe_trajectory",
    "pb_trajectory",
    "dividend_policy",
    "ev_multiples",
    "peer_comparison",
    "other",
]
