"""Schemas for the Management & Governance Agent.

Evidence here is *textual* (a quote from the annual report) rather than
numeric. Same anti-generic discipline as the Financials/Valuation agents:
strict length and shape constraints make hand-wavy output structurally
impossible.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DISCLAIMER

ManagementFindingCategory = Literal[
    "operational_performance",
    "guidance",
    "capital_allocation",
    "board_composition",
    "audit",
    "remuneration",
    "related_party_transactions",
    "shareholder_returns",
    "esg_disclosure",
    "other",
]


class TextEvidence(BaseModel):
    """A direct quote from the annual report, plus where it came from."""

    model_config = ConfigDict(frozen=True)

    quote: str = Field(
        ...,
        min_length=20,
        max_length=600,
        description=(
            "A near-verbatim quote from the annual report. May be lightly "
            "trimmed (e.g. ellipsis) to fit the limit but MUST preserve the "
            "substantive language — paraphrasing is not allowed."
        ),
    )
    section: Literal["mda", "governance", "risks", "directors_report"]
    page: int | None = Field(
        default=None,
        description="Page number in the source PDF, when known.",
    )


class ManagementFinding(BaseModel):
    """One management/governance observation, anchored to a quote."""

    model_config = ConfigDict(frozen=True)

    claim: str = Field(
        ...,
        min_length=30,
        max_length=400,
        description=(
            "A specific observation about management commentary or governance "
            "practice. MUST be evidence-linked. Generic vocabulary "
            "('strong', 'robust', 'best-in-class', 'world-class', "
            "'committed to', 'continues to') is BANNED — replace with the "
            "concrete fact and quote."
        ),
    )
    category: ManagementFindingCategory
    evidence: list[TextEvidence] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="At least one quote per finding. Empty evidence is rejected.",
    )


class ManagementReport(BaseModel):
    """Output of the Management Agent."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    yfinance_symbol: str
    company_name: str | None = None
    fiscal_year: int | None = Field(
        default=None,
        description="Fiscal year of the annual report this report draws from (e.g. 2025).",
    )
    annual_report_url: str | None = None
    annual_report_page_count: int | None = None
    mda_findings: list[ManagementFinding] = Field(
        ...,
        min_length=0,
        max_length=5,
        description=(
            "Up to 5 evidence-linked findings drawn from the Management "
            "Discussion & Analysis section. Empty if MD&A unavailable."
        ),
    )
    governance_findings: list[ManagementFinding] = Field(
        ...,
        min_length=0,
        max_length=5,
        description=(
            "Up to 5 evidence-linked findings drawn from the Corporate "
            "Governance section. Empty if section unavailable."
        ),
    )
    data_quality_notes: list[str] = Field(default_factory=list)
    generated_at: datetime
    disclaimer: str = Field(default=DISCLAIMER)
