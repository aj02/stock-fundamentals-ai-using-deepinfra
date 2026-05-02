"""Risk Agent.

Tools:
  - annual_report_extract_risks — pulls the Risk Management section from the
    latest AR (or a risks subsection nested inside MD&A — the AR extractor
    handles both cases).
  - screener_fetch_concerns — pulls Screener.in's "Cons" bullets, which
    surface concrete concerns (e.g. "low return on equity over last 3 years",
    "low dividend payout") that supplement the AR's typically-broad
    risk disclosures.

Output: a categorised, severity-tagged list of risks, each anchored to a
quote from one of the two sources.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import structlog
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, RunContext

from app.agents.deps import AgentDeps
from app.agents.llm import ModelTier, build_model
from app.core.config import get_settings
from app.schemas.risk import RiskReport

log = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are a risk analyst reading the LATEST annual report of an Indian listed
company plus its Screener.in concern bullets. Produce a `RiskReport`
containing 0-10 specific, categorised, severity-tagged risks.

═══════════════════════════════════════════════════════════════════════════
WORKFLOW
═══════════════════════════════════════════════════════════════════════════
1. Call `annual_report_extract_risks(ticker)`. The tool returns either:
   - A Risk Management section (`available: true`), OR
   - `available: false` if no risks section was matched. In Indian ARs the
     risks content is sometimes nested inside MD&A — if you see risk-like
     language inside MD&A, it's still fine to use; cite the section the
     quote came from.
2. Call `screener_fetch_concerns(ticker)`. Returns a list of bullet-form
   concerns (e.g. "Company has a low return on equity of 8.91% over last 3
   years"). Set `screener_concerns_used = True` only if at least one
   finding cites a Screener bullet.
3. Produce 0–10 risks. Each risk is ONE specific issue, not a list. If the
   AR is generic (boilerplate disclosures only), produce fewer findings —
   empty lists are acceptable.

═══════════════════════════════════════════════════════════════════════════
RULES — STRICT
═══════════════════════════════════════════════════════════════════════════
- EVERY finding has at least one `RiskEvidence` quote (20-600 chars).
- Quotes are NEAR-VERBATIM from the source — paraphrasing not allowed.
- One risk per finding. "Geopolitical risk including supply chain, currency,
  and commodity volatility" is FOUR risks; split them.
- Categorise into: business, financial, regulatory, operational, market,
  esg, other. Cover at least three distinct categories when the AR raises
  material risks across them.
- Severity is DESCRIPTIVE not PREDICTIVE:
    high   = explicitly disclosed AND has near-term financial materiality
             (specific magnitude, recent occurrence, or active impact).
    medium = explicitly disclosed AND specifically applicable to this
             company, but mitigation is described or impact is moderate.
    low    = boilerplate disclosure (every Indian AR mentions it; no
             specific magnitude attached to this issuer).
- `mitigation_summary` is one sentence, ONLY if the company explicitly
  describes a mitigation. Otherwise leave it None — don't invent.

────── BANNED PHRASES ──────
"significant risk", "material impact", "could affect", "may have an
adverse effect", "subject to various risks", "various uncertainties",
"there can be no assurance", "we are exposed to" (use only inside QUOTES,
never in your `risk` field).

The `risk` field uses YOUR words to name the specific issue: "Currency
mismatch on USD-denominated borrowings against INR cash flows" beats
"Foreign exchange risk."

────── DESCRIPTIVE ONLY ──────
- Do NOT recommend buying, selling, or holding.
- Do NOT speculate beyond what sources say.
- Do NOT add risks that are not in the source material.
- Do NOT compare risk levels to "industry average" or peers.

═══════════════════════════════════════════════════════════════════════════
EVIDENCE EXAMPLES
═══════════════════════════════════════════════════════════════════════════

GOOD (specific, narrow, source-anchored):
{
  "risk": "Refining margin compression from sustained crude-product spread \
narrowing — FY24 GRM normalised from elevated FY23 levels and remained \
range-bound thereafter.",
  "category": "market",
  "severity": "high",
  "mitigation_summary": "Diversification into petrochemicals and integrated \
oil-to-chemicals reduces direct GRM sensitivity, per MD&A.",
  "evidence": [
    {"quote": "Gross refining margins normalised from the elevated FY23 \
levels driven by a steeper drop in middle-distillate spreads.", \
"source": "annual_report", "section": "mda"}
  ]
}

GOOD (Screener bullet quoted directly):
{
  "risk": "ROE has averaged below 9% over the last three years, suggesting \
limited returns on the expanding equity base.",
  "category": "financial",
  "severity": "medium",
  "mitigation_summary": null,
  "evidence": [
    {"quote": "Company has a low return on equity of 8.91% over last 3 \
years.", "source": "screener_concern", "section": null}
  ]
}

BAD (vague, unanchored, generic vocabulary — DO NOT EMIT):
{
  "risk": "The company is exposed to various business and market risks \
that could have a material adverse effect on operations.",
  ...
}
"""


class _RisksToolResponse(BaseModel):
    """Flat response shape for the AR-risks extraction tool."""

    model_config = ConfigDict(frozen=True)

    available: bool
    fiscal_year: int | None = None
    source_url: str | None = None
    section_used: Literal["risks", "mda", "none"] = "none"
    heading_found: str | None = None
    text: str | None = None
    word_count: int | None = None
    truncated: bool | None = None
    note: str | None = None


class _ConcernsToolResponse(BaseModel):
    """Flat response shape for the Screener concerns tool."""

    model_config = ConfigDict(frozen=True)

    available: bool
    concerns: list[str] = []
    note: str | None = None


def _build_agent() -> Agent[AgentDeps, RiskReport]:
    settings = get_settings()
    agent = Agent[AgentDeps, RiskReport](
        model=build_model(ModelTier.AGENT, settings),
        deps_type=AgentDeps,
        output_type=RiskReport,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.tool
    async def annual_report_extract_risks(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> _RisksToolResponse:
        """Extract the Risk Management section (or MD&A fallback if risks
        section is nested inside MD&A and not separately matched).
        """
        log.info("agent.risk.tool.extract_risks", ticker=ticker)
        snap = await ctx.deps.annual_report_service.fetch_and_extract(
            ticker, sections=["mda", "risks"]
        )
        if not snap.available:
            return _RisksToolResponse(
                available=False,
                fiscal_year=snap.fiscal_year,
                source_url=snap.source_url,
                note=snap.note,
            )
        # Prefer a dedicated risks section if found; otherwise fall back to
        # MD&A (where risks are nested in many Indian ARs).
        risks_sect = snap.sections.get("risks")
        if risks_sect is not None:
            return _RisksToolResponse(
                available=True,
                fiscal_year=snap.fiscal_year,
                source_url=snap.source_url,
                section_used="risks",
                heading_found=risks_sect.heading_found,
                text=risks_sect.text,
                word_count=risks_sect.word_count,
                truncated=risks_sect.truncated,
            )
        mda_sect = snap.sections.get("mda")
        if mda_sect is not None:
            return _RisksToolResponse(
                available=True,
                fiscal_year=snap.fiscal_year,
                source_url=snap.source_url,
                section_used="mda",
                heading_found=mda_sect.heading_found,
                text=mda_sect.text,
                word_count=mda_sect.word_count,
                truncated=mda_sect.truncated,
                note="No standalone risks section matched; using MD&A which often contains nested risk discussion.",
            )
        return _RisksToolResponse(
            available=False,
            fiscal_year=snap.fiscal_year,
            source_url=snap.source_url,
            note="Neither risks nor MD&A section available.",
        )

    @agent.tool
    async def screener_fetch_concerns(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> _ConcernsToolResponse:
        """Return Screener.in's 'Cons' bullets — concrete, often quantitative
        concerns about the company.
        """
        log.info("agent.risk.tool.screener_concerns", ticker=ticker)
        snap = await ctx.deps.screener_scraper.fetch_company(ticker)
        if not snap.available:
            return _ConcernsToolResponse(
                available=False,
                concerns=[],
                note=snap.note or "Screener data unavailable",
            )
        return _ConcernsToolResponse(
            available=True,
            concerns=snap.cons,
            note=None if snap.cons else "Screener returned no concern bullets",
        )

    return agent


_agent: Agent[AgentDeps, RiskReport] | None = None


def get_risk_agent() -> Agent[AgentDeps, RiskReport]:
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


async def run_risk_agent(ticker: str, deps: AgentDeps) -> RiskReport:
    agent = get_risk_agent()
    log.info("agent.risk.run.start", ticker=ticker)

    user_prompt = (
        f"Produce a RiskReport for ticker {ticker.upper()}. "
        "Call both extraction tools. Categorise each risk; tag severity "
        "according to the rubric (descriptive, not predictive). Every risk "
        "must include a near-verbatim quote from one of the two sources."
    )

    result = await agent.run(user_prompt, deps=deps)
    report = result.output

    snapshot = await deps.yfinance_client.fetch_financials(ticker)
    ar_snap = await deps.annual_report_service.fetch_and_extract(
        ticker, sections=["mda", "risks"]
    )
    report = report.model_copy(
        update={
            "ticker": ticker.upper(),
            "yfinance_symbol": snapshot.yfinance_symbol,
            "company_name": snapshot.company_name,
            "fiscal_year": ar_snap.fiscal_year,
            "annual_report_url": ar_snap.source_url,
            "generated_at": datetime.now(UTC),
        }
    )

    log.info(
        "agent.risk.run.done",
        ticker=ticker,
        fiscal_year=report.fiscal_year,
        risks=len(report.risks),
        screener_concerns_used=report.screener_concerns_used,
    )
    return report
