"""Schemas for the Risk Agent.

Same evidence-discipline as Management: every risk finding cites a quote
from the AR or a Screener concern bullet. Risks are categorised + severity-
tagged so downstream consumers (Thesis Agent, UI) can filter / sort.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DISCLAIMER

RiskCategory = Literal[
    "business",
    "financial",
    "regulatory",
    "operational",
    "market",
    "esg",
    "other",
]

RiskSeverity = Literal["low", "medium", "high"]


class RiskEvidence(BaseModel):
    """Evidence backing a single risk — quote from AR section or Screener bullet."""

    model_config = ConfigDict(frozen=True)

    quote: str = Field(
        ...,
        min_length=20,
        max_length=600,
        description=(
            "Near-verbatim quote from the source — annual-report risks/MD&A "
            "section OR a Screener.in concern bullet. Lightly trimmed is OK; "
            "paraphrasing is not."
        ),
    )
    source: Literal["annual_report", "screener_concern", "mda"]
    section: Literal["mda", "governance", "risks", "directors_report"] | None = Field(
        default=None,
        description=(
            "Which annual-report section the quote came from. None when "
            "source='screener_concern'."
        ),
    )
    page: int | None = None


class RiskFinding(BaseModel):
    """One categorised, severity-tagged risk."""

    model_config = ConfigDict(frozen=True)

    risk: str = Field(
        ...,
        min_length=20,
        max_length=300,
        description=(
            "A specific, narrow risk statement (one risk per finding, not a "
            "list). Generic vocabulary BANNED — see system prompt."
        ),
    )
    category: RiskCategory
    severity: RiskSeverity = Field(
        ...,
        description=(
            "Severity is descriptive, not predictive: 'high' = the risk is "
            "explicitly disclosed by the company AND has near-term materiality "
            "on the financials; 'medium' = explicitly disclosed but managed/"
            "mitigated; 'low' = boilerplate disclosure with no specific "
            "magnitude attached."
        ),
    )
    mitigation_summary: str | None = Field(
        default=None,
        max_length=400,
        description=(
            "One-sentence summary of any mitigation the company explicitly "
            "describes. Leave None if no mitigation is mentioned."
        ),
    )
    evidence: list[RiskEvidence] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="At least one quote per risk. Empty evidence is rejected.",
    )


class RiskReport(BaseModel):
    """Output of the Risk Agent."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    yfinance_symbol: str
    company_name: str | None = None
    fiscal_year: int | None = None
    annual_report_url: str | None = None
    risks: list[RiskFinding] = Field(
        ...,
        min_length=0,
        max_length=10,
        description=(
            "0–10 categorised risks. Cover at least three different "
            "categories from {business, financial, regulatory, operational, "
            "market} when material risks exist."
        ),
    )
    screener_concerns_used: bool = Field(
        default=False,
        description="True if Screener.in concern bullets contributed to any finding.",
    )
    data_quality_notes: list[str] = Field(default_factory=list)
    generated_at: datetime
    disclaimer: str = Field(default=DISCLAIMER)
