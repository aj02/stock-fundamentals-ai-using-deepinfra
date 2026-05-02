"""Schemas for annual-report extraction."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ARSectionType = Literal["mda", "governance", "risks", "directors_report"]


class AnnualReportSection(BaseModel):
    """A single extracted section of an annual report."""

    model_config = ConfigDict(frozen=True)

    section_type: ARSectionType
    heading_found: str = Field(
        ...,
        description="The actual heading text matched in the PDF, e.g. 'Management Discussion and Analysis'.",
    )
    page_start: int | None = None
    page_end: int | None = None
    text: str
    word_count: int
    truncated: bool = Field(
        default=False,
        description="True if the section was truncated to fit the LLM token budget.",
    )


class AnnualReportSnapshot(BaseModel):
    """Result of parsing one company's latest annual report."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    available: bool = False
    fiscal_year: int | None = None
    source_url: str | None = None
    page_count: int | None = None
    sections: dict[ARSectionType, AnnualReportSection] = Field(default_factory=dict)
    note: str | None = None
    fetched_at: datetime
