"""Management & Governance Agent.

Tools:
  - annual_report_extract_md_a — extracts MD&A section from latest AR.
  - annual_report_extract_governance — extracts Corporate Governance section.

Strict scope (per spec): only MD&A + governance from the LATEST annual
report. Risk Factors are the Risk Agent's territory; financial-statement
notes belong to the Financials Agent. The agent is instructed to refuse
findings outside MD&A/governance even if present in the tool output.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic_ai import Agent, RunContext

from app.agents.deps import AgentDeps
from app.agents.llm import ModelTier, build_model
from app.core.config import get_settings
from app.schemas.annual_report import AnnualReportSection
from app.schemas.management import ManagementReport

log = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are a corporate-governance and management-commentary analyst reading the
LATEST published annual report of an Indian listed company. Your job is to
produce a `ManagementReport` containing two short lists of findings:

  - mda_findings: 0-5 observations from the Management Discussion & Analysis
    section. Operational performance, segment commentary, forward-looking
    statements, capital-allocation language.
  - governance_findings: 0-5 observations from the Corporate Governance
    section. Board composition, audit, remuneration, related-party
    transactions, shareholder returns.

═══════════════════════════════════════════════════════════════════════════
WORKFLOW (follow exactly)
═══════════════════════════════════════════════════════════════════════════
1. Call `annual_report_extract_md_a(ticker)`. If it returns
   `available: false`, leave `mda_findings = []` and add a data-quality note.
2. Call `annual_report_extract_governance(ticker)`. Same rule on
   `available: false`.
3. Read each returned section carefully. The `text` field contains an
   excerpt of up to 5000 words from the actual annual report — treat it
   as authoritative source material.
4. Produce 0–5 findings per section based on what is ACTUALLY IN THE TEXT.
   Do NOT invent. Do NOT pull in knowledge from outside the provided text.
   If a section is short or generic, produce fewer findings — empty lists
   are acceptable.

═══════════════════════════════════════════════════════════════════════════
EVIDENCE RULES — STRICT
═══════════════════════════════════════════════════════════════════════════
- EVERY finding must include at least one `TextEvidence` with a
  near-verbatim quote (20–600 chars) from the relevant section.
- The `quote` MUST be a substring (or near-verbatim, lightly trimmed) of
  the section text. Do NOT paraphrase. Do NOT summarise into the quote
  field — quotes are for direct lifting.
- Set `evidence.section` to the section the quote came from
  ('mda' or 'governance'). Set `evidence.page` if you can infer it from
  context (otherwise leave None).
- The `claim` field is YOUR observation, written in your own words. The
  `quote` field is the company's words.

────── BANNED PHRASES IN CLAIMS ──────
"strong", "robust", "healthy", "best-in-class", "world-class",
"impressive", "premier", "stellar", "outstanding", "committed to",
"continues to", "remains focused on", "well-positioned", "is poised to",
"looks forward to", "tremendous", "industry-leading".

If you find yourself reaching for one of these, STOP. State the concrete
fact: what specifically did the company say or disclose? "The Chairman's
letter cites a target of 50% revenue contribution from new energy by 2030"
beats "the company is well-positioned in new energy."

────── DESCRIPTIVE ONLY ──────
- Do NOT recommend buying, selling, or holding.
- Do NOT speculate beyond what the text says.
- Do NOT compare to peers or to the broader market.
- Do NOT repeat content already covered by the Financials Agent (numbers,
  ratios). Focus on what management SAID, not what they REPORTED.

═══════════════════════════════════════════════════════════════════════════
EVIDENCE EXAMPLE
═══════════════════════════════════════════════════════════════════════════

GOOD MD&A finding:
{
  "claim": "Management explicitly identified retail and digital services as \
the two engines of medium-term growth, with retail's store count \
growing past 18,000 in FY25.",
  "category": "operational_performance",
  "evidence": [
    {"quote": "Reliance Retail crossed 18,000 stores in FY25, with digital \
commerce contributing over 18% of revenue across formats.", "section": "mda"}
  ]
}

GOOD governance finding:
{
  "claim": "The board has 9 of 12 directors classified as independent, with \
the audit committee chaired by an independent director and meeting four \
times during FY25.",
  "category": "board_composition",
  "evidence": [
    {"quote": "Of the twelve directors, nine are Independent Non-Executive \
Directors. The Audit Committee, chaired by Mr. K.V. Chowdary, met four \
times during the year.", "section": "governance"}
  ]
}

BAD finding (banned vocabulary, vague — DO NOT EMIT):
{
  "claim": "The company is well-positioned for growth and committed to \
strong governance practices.",
  ...
}
"""


def _build_agent() -> Agent[AgentDeps, ManagementReport]:
    settings = get_settings()
    agent = Agent[AgentDeps, ManagementReport](
        model=build_model(ModelTier.AGENT, settings),
        deps_type=AgentDeps,
        output_type=ManagementReport,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.tool
    async def annual_report_extract_md_a(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> AnnualReportSectionResponse:
        """Extract the Management Discussion & Analysis section.

        Returns the section text (truncated to ~5000 words) plus
        availability metadata. If `available` is false, the underlying
        annual report could not be discovered or parsed; in that case
        leave mda_findings empty and add a data-quality note.
        """
        log.info("agent.management.tool.extract_mda", ticker=ticker)
        snapshot = await ctx.deps.annual_report_service.fetch_and_extract(
            ticker, sections=["mda", "governance"]
        )
        section = snapshot.sections.get("mda") if snapshot.available else None
        return AnnualReportSectionResponse.from_pieces(
            available=section is not None,
            section=section,
            fiscal_year=snapshot.fiscal_year,
            source_url=snapshot.source_url,
            note=snapshot.note,
        )

    @agent.tool
    async def annual_report_extract_governance(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> AnnualReportSectionResponse:
        """Extract the Corporate Governance section."""
        log.info("agent.management.tool.extract_governance", ticker=ticker)
        snapshot = await ctx.deps.annual_report_service.fetch_and_extract(
            ticker, sections=["mda", "governance"]
        )
        section = snapshot.sections.get("governance") if snapshot.available else None
        return AnnualReportSectionResponse.from_pieces(
            available=section is not None,
            section=section,
            fiscal_year=snapshot.fiscal_year,
            source_url=snapshot.source_url,
            note=snapshot.note,
        )

    return agent


# Tool response wrapper — flat shape so PydanticAI's tool-arg machinery is happy.
from pydantic import BaseModel, ConfigDict, Field


class AnnualReportSectionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    fiscal_year: int | None = None
    source_url: str | None = None
    heading_found: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    text: str | None = None
    word_count: int | None = None
    truncated: bool | None = None
    note: str | None = None

    @classmethod
    def from_pieces(
        cls,
        available: bool,
        section: AnnualReportSection | None,
        fiscal_year: int | None,
        source_url: str | None,
        note: str | None,
    ) -> AnnualReportSectionResponse:
        if not available or section is None:
            return cls(
                available=False,
                fiscal_year=fiscal_year,
                source_url=source_url,
                note=note or "Section unavailable",
            )
        return cls(
            available=True,
            fiscal_year=fiscal_year,
            source_url=source_url,
            heading_found=section.heading_found,
            page_start=section.page_start,
            page_end=section.page_end,
            text=section.text,
            word_count=section.word_count,
            truncated=section.truncated,
            note=None,
        )


_agent: Agent[AgentDeps, ManagementReport] | None = None


def get_management_agent() -> Agent[AgentDeps, ManagementReport]:
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


async def run_management_agent(ticker: str, deps: AgentDeps) -> ManagementReport:
    agent = get_management_agent()
    log.info("agent.management.run.start", ticker=ticker)

    user_prompt = (
        f"Produce a ManagementReport for ticker {ticker.upper()}. "
        "Call both extraction tools. If a section is unavailable, leave its "
        "findings list empty and note it in data_quality_notes. Every "
        "finding must include a near-verbatim quote from the relevant "
        "annual-report section."
    )

    result = await agent.run(user_prompt, deps=deps)
    report = result.output

    # Overlay deterministic identity. We re-fetch the snapshot once to get
    # the fiscal_year / source_url, but the agent already used the cached
    # version, so the second call is free.
    snapshot = await deps.yfinance_client.fetch_financials(ticker)
    ar_snap = await deps.annual_report_service.fetch_and_extract(
        ticker, sections=["mda", "governance"]
    )
    report = report.model_copy(
        update={
            "ticker": ticker.upper(),
            "yfinance_symbol": snapshot.yfinance_symbol,
            "company_name": snapshot.company_name,
            "fiscal_year": ar_snap.fiscal_year,
            "annual_report_url": ar_snap.source_url,
            "annual_report_page_count": ar_snap.page_count,
            "generated_at": datetime.now(UTC),
        }
    )

    log.info(
        "agent.management.run.done",
        ticker=ticker,
        fiscal_year=report.fiscal_year,
        mda_findings=len(report.mda_findings),
        gov_findings=len(report.governance_findings),
    )
    return report
