"""Pydantic output schemas for the agents.

These shapes are deliberately strict — `min_length` constraints on evidence
links and the qualitative-assessment list make it structurally hard for the
LLM to produce vague output. If a finding has no values cited, validation
fails and the agent is forced to retry.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DISCLAIMER

FindingCategory = Literal[
    "growth",
    "profitability",
    "leverage",
    "cash_generation",
    "capital_efficiency",
    "earnings_quality",
    "other",
]


class EvidenceLink(BaseModel):
    """Anchors a qualitative claim to specific computed values."""

    model_config = ConfigDict(frozen=True)

    metric: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description=(
            "Name of the metric used as evidence, e.g. 'Net margin (%)', "
            "'OCF/PAT', 'Debt/Equity', 'Revenue (₹ cr)'."
        ),
    )
    years_referenced: list[int] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Fiscal-year-ending years (e.g. [2024, 2025, 2026]).",
    )
    values: list[float] = Field(
        ...,
        min_length=1,
        max_length=5,
        description=(
            "Numeric values aligned positionally with `years_referenced`. "
            "Same length as years_referenced. Use the same unit as `metric`."
        ),
    )


class QualitativeFinding(BaseModel):
    """One specific, evidence-linked observation about the financials."""

    model_config = ConfigDict(frozen=True)

    claim: str = Field(
        ...,
        min_length=30,
        max_length=400,
        description=(
            "A specific, evidence-grounded observation. MUST mention at least "
            "one numeric value with its year in plain English (e.g. 'Revenue "
            "grew 14.2 percent CAGR from FY23 ₹8.78L cr to FY26 ₹10.57L cr'). "
            "Generic phrasing ('strong fundamentals', 'market leader', 'healthy', "
            "'robust', 'solid', 'best-in-class') is BANNED — replace with the "
            "metric and number."
        ),
    )
    category: FindingCategory = Field(
        ...,
        description="Which dimension of fundamentals this finding speaks to.",
    )
    evidence: list[EvidenceLink] = Field(
        ...,
        min_length=1,
        max_length=4,
        description="At least one EvidenceLink. No empty evidence allowed.",
    )


class YearlyRatios(BaseModel):
    """Computed ratios for a single fiscal year. Newest-first in the report."""

    model_config = ConfigDict(frozen=True)

    period_end: date
    gross_margin_pct: float | None = None
    operating_margin_pct: float | None = None
    net_margin_pct: float | None = None
    roe_pct: float | None = None
    roce_pct: float | None = None
    debt_to_equity: float | None = None
    interest_coverage: float | None = None
    current_ratio: float | None = None
    ocf_to_pat: float | None = None
    fcf_margin_pct: float | None = None


class GrowthRates(BaseModel):
    model_config = ConfigDict(frozen=True)

    revenue_cagr_3y_pct: float | None = None
    revenue_cagr_5y_pct: float | None = None
    net_income_cagr_3y_pct: float | None = None
    net_income_cagr_5y_pct: float | None = None
    fcf_cagr_3y_pct: float | None = None


class RatiosTable(BaseModel):
    model_config = ConfigDict(frozen=True)

    yearly: list[YearlyRatios] = Field(default_factory=list, description="Newest first.")
    growth: GrowthRates


class YearlyDataPoint(BaseModel):
    """Compact view of a single year — what ends up rendered in the report's data table."""

    model_config = ConfigDict(frozen=True)

    period_end: date
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    total_debt: float | None = None
    total_equity: float | None = None


class FinancialsReport(BaseModel):
    """Output of the Financials Agent.

    The agent populates the qualitative_assessment list — every other field
    is computed deterministically from the yfinance snapshot, so the LLM is
    only responsible for *interpretation*, not for the numbers.
    """

    model_config = ConfigDict(frozen=True)

    ticker: str
    yfinance_symbol: str
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str = "INR"
    period_summary: str = Field(
        ...,
        description="Human-readable range, e.g. 'FY2022 to FY2026 (5 years)'.",
    )
    yearly_data: list[YearlyDataPoint] = Field(
        default_factory=list, description="Newest first."
    )
    ratios: RatiosTable
    qualitative_assessment: list[QualitativeFinding] = Field(
        ...,
        min_length=4,
        max_length=7,
        description=(
            "4-7 evidence-linked findings. MUST cover at least three of "
            "{growth, profitability, leverage, cash_generation, capital_efficiency}. "
            "DESCRIPTIVE only — no buy/sell/hold language, no 'score', no "
            "peer comparison (peers are the Valuation Agent's job)."
        ),
    )
    data_quality_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Plain-English notes about missing or anomalous data, e.g. "
            "'FY2022 income statement missing from yfinance.'"
        ),
    )
    generated_at: datetime
    disclaimer: str = Field(default=DISCLAIMER)
