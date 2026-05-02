"""Schemas for the Thesis Agent (synthesis only).

The Thesis Agent's job is to read the prior 4 agent outputs and produce a
bull case + bear case + neutral summary. EVERY point in bull/bear must
cite which prior-agent finding it derives from. This makes the synthesis
auditable: a reader can trace any claim back to its source.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DISCLAIMER

ThesisSourceAgent = Literal["financials", "valuation", "management", "risk"]


class ThesisCitation(BaseModel):
    """Pointer to the prior-agent finding this thesis point draws from."""

    model_config = ConfigDict(frozen=True)

    source_agent: ThesisSourceAgent = Field(
        ...,
        description="Which prior agent produced the finding being cited.",
    )
    finding_index: int = Field(
        ...,
        ge=0,
        description=(
            "0-based index into the source agent's findings list. Use the "
            "exact index from the synthesis prompt — do NOT renumber."
        ),
    )
    summary: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description=(
            "One-sentence reminder of what the cited finding said. This is "
            "for the reader's benefit; the source_agent + finding_index is "
            "the canonical link."
        ),
    )


class ThesisPoint(BaseModel):
    """A single bull or bear point. MUST cite at least one prior finding."""

    model_config = ConfigDict(frozen=True)

    point: str = Field(
        ...,
        min_length=30,
        max_length=400,
        description=(
            "A specific, evidence-based observation framed as a bull or bear "
            "consideration (NOT a recommendation, NOT a price target). "
            "Example: 'OCF/PAT consistently above 2x for 3 of 4 years suggests "
            "high earnings quality (cited from Financials finding 4).'"
        ),
    )
    citations: list[ThesisCitation] = Field(
        ...,
        min_length=1,
        max_length=4,
        description="At least one citation. NO uncited bull/bear points.",
    )


class InvestmentThesis(BaseModel):
    """Output of the Thesis Agent."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    company_name: str | None = None
    bull_case: list[ThesisPoint] = Field(
        ...,
        min_length=2,
        max_length=6,
        description="2–6 bull-case points, each with at least one citation.",
    )
    bear_case: list[ThesisPoint] = Field(
        ...,
        min_length=2,
        max_length=6,
        description="2–6 bear-case points, each with at least one citation.",
    )
    neutral_summary: str = Field(
        ...,
        min_length=80,
        max_length=600,
        description=(
            "A 2–4 sentence neutral synthesis describing what the financials "
            "+ valuation + management + risk picture jointly says. NO buy/sell "
            "language, NO 'fair value', NO price target."
        ),
    )
    sections_unavailable: list[ThesisSourceAgent] = Field(
        default_factory=list,
        description=(
            "Which prior agents had to be skipped (e.g. Management Agent "
            "unavailable because the AR could not be parsed). The thesis "
            "should still be producible from whatever DID succeed."
        ),
    )
    generated_at: datetime
    disclaimer: str = Field(default=DISCLAIMER)
