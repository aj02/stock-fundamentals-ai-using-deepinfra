"""Top-level RunReport — the structured output of POST /analyze.

Bundles the five agent outputs (or marks them unavailable on partial
failure) plus the synthesised thesis. Every API response that returns a
RunReport carries the project disclaimer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DISCLAIMER
from app.schemas.agents import FinancialsReport
from app.schemas.management import ManagementReport
from app.schemas.risk import RiskReport
from app.schemas.thesis import InvestmentThesis
from app.schemas.valuation import ValuationReport

RunDepth = Literal["quick", "full"]
RunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class SectionUnavailable(BaseModel):
    """Explicit marker that an agent failed/skipped — recorded in the report
    so consumers can show 'unavailable' rather than silently omit.
    """

    model_config = ConfigDict(frozen=True)

    section: Literal["financials", "valuation", "management", "risk", "thesis"]
    reason: str = Field(..., min_length=1, max_length=300)


class RunReport(BaseModel):
    """Final structured output of one analysis run."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    ticker: str
    depth: RunDepth
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    # Agent outputs — any of these may be None if the agent failed/skipped
    # on a "full" run (or wasn't part of a "quick" run).
    financials: FinancialsReport | None = None
    valuation: ValuationReport | None = None
    management: ManagementReport | None = None
    risk: RiskReport | None = None
    thesis: InvestmentThesis | None = None

    unavailable_sections: list[SectionUnavailable] = Field(default_factory=list)
    error: str | None = None
    disclaimer: str = Field(default=DISCLAIMER)
