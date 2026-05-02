"""Financials Agent — first PydanticAI agent in the orchestra.

Responsibilities:
- Pull 5-year financials via the yfinance tool.
- Get computed ratios via the compute_ratios tool (the actual math runs in
  Python, not in the LLM — see app.services.ratios).
- Optionally consult Screener.in (currently a stub returning available=False).
- Produce a `FinancialsReport`: data table + ratios + 4-7 evidence-linked
  qualitative findings + data-quality notes.

Anti-generic strategy is layered:
1. The Pydantic schema rejects empty evidence lists and short claim strings.
2. The system prompt names banned phrases and shows good/bad examples.
3. The agent uses Sonnet (not Haiku) so it can handle nuance.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic_ai import Agent, RunContext

from app.agents.deps import AgentDeps
from app.agents.llm import ModelTier, build_model
from app.core.config import get_settings
from app.schemas.agents import (
    FinancialsReport,
    RatiosTable,
    YearlyDataPoint,
)
from app.schemas.financials import FinancialsSnapshot, ScreenerSnapshot
from app.services.ratios import compute_ratios as _compute_ratios_pure

log = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are a financial analyst examining the 5-year financial trajectory of an Indian
listed company (NSE/BSE). Your job is to produce a `FinancialsReport`.

═══════════════════════════════════════════════════════════════════════════
WORKFLOW (follow exactly)
═══════════════════════════════════════════════════════════════════════════
1. Call `yfinance_fetch_financials(ticker)` — returns 5-year income, balance
   sheet, and cash-flow data.
2. Call `compute_ratios(ticker)` — returns the deterministic ratios table.
   Do NOT compute ratios yourself; use this tool's output verbatim.
3. (Optional) Call `screener_fetch_financials(ticker)`. If the response has
   `available: false`, IGNORE it and proceed with yfinance data alone.
4. Produce the `FinancialsReport`. Populate `yearly_data`, `ratios`,
   `qualitative_assessment`, and `data_quality_notes` using the tool outputs.

═══════════════════════════════════════════════════════════════════════════
QUALITATIVE ASSESSMENT — STRICT RULES
═══════════════════════════════════════════════════════════════════════════
- Produce 4–7 findings. Each finding is 1–2 sentences max.
- Cover at least three different categories from
  {growth, profitability, leverage, cash_generation, capital_efficiency,
   earnings_quality}.
- EVERY claim must mention specific numbers with their year(s) in plain English.
  Example: "Net margin compressed from 7.6% in FY23 to 7.4% in FY26 even as
  revenue grew 14.2% CAGR over the same period."
- EVERY finding must include at least one `EvidenceLink` with the metric
  name, the years referenced, and the actual values.

────── BANNED PHRASES — do not use any of these ──────
"strong fundamentals", "robust", "solid", "healthy", "good", "great",
"impressive", "best-in-class", "market leader", "industry leader",
"the company is performing well", "consistent performer", "high quality",
"reliable", "promising", "encouraging", "well-positioned",
"world-class", "premier", "stellar", "outstanding".

If you find yourself reaching for one of these words, STOP. Replace with the
specific metric name and number(s) that the word was supposed to summarise.

────── DESCRIPTIVE ONLY — do NOT do these ──────
- Do NOT recommend buying, selling, or holding.
- Do NOT assign a numeric score, rating, or grade.
- Do NOT compare to peers or to the broader market — peer comparison is the
  Valuation Agent's job, not yours.
- Do NOT speculate about future stock price.
- Do NOT use forward-looking language ("will continue to", "should grow") —
  describe what the past 5 years actually showed.

═══════════════════════════════════════════════════════════════════════════
EVIDENCE EXAMPLES
═══════════════════════════════════════════════════════════════════════════

GOOD finding (specific, numeric, evidence-linked, descriptive):
{
  "claim": "Operating cash flow exceeded reported PAT every year from FY23 \
to FY26 — OCF/PAT averaged 2.24× over the period — indicating reported \
earnings were backed by cash generation.",
  "category": "earnings_quality",
  "evidence": [
    {"metric": "OCF/PAT", "years_referenced": [2023, 2024, 2025, 2026],
     "values": [1.72, 2.28, 2.57, 2.38]}
  ]
}

BAD finding (generic, unanchored, banned vocabulary — DO NOT EMIT):
{
  "claim": "The company has strong cash generation and is performing well.",
  "category": "cash_generation",
  "evidence": [...]
}

GOOD finding (numeric trajectory, named years):
{
  "claim": "Total debt rose from ₹3.34 lakh crore in FY23 to ₹3.98 lakh \
crore in FY26 (+19% over 3 years) while total equity rose 26% over the \
same span, leaving Debt/Equity roughly flat at ~0.44x.",
  "category": "leverage",
  "evidence": [
    {"metric": "Total Debt (₹ cr)", "years_referenced": [2023, 2026],
     "values": [334392.0, 398000.0]},
    {"metric": "Debt/Equity", "years_referenced": [2023, 2026],
     "values": [0.467, 0.440]}
  ]
}

═══════════════════════════════════════════════════════════════════════════
DATA QUALITY
═══════════════════════════════════════════════════════════════════════════
Many Indian-equity yfinance feeds are missing the oldest year (FY22 frequently
shows up empty). Note such gaps in `data_quality_notes` rather than ignoring
them.

═══════════════════════════════════════════════════════════════════════════
CURRENCY
═══════════════════════════════════════════════════════════════════════════
First check `currency` on the FinancialsSnapshot returned by
`yfinance_fetch_financials`. yfinance reports most NSE/BSE-listed companies
in INR, but some (notably Infosys, Wipro and a few other IT exporters)
return in USD because that is their functional reporting currency.

INR REPORTING (most companies):
  - yfinance returns absolute INR (e.g. 10,572,190,000,000 = ₹10.57 lakh
    crore of revenue).
  - In claim text, prefer compact units: "₹10.57 lakh crore" or
    "₹10.57L cr" — never the raw 13-digit number.
  - In `EvidenceLink.values`, prefer ₹ crore (i.e. raw INR ÷ 1,00,00,000).
    Make the unit explicit in `metric`, e.g. "Revenue (₹ cr)".

USD REPORTING (Infosys etc.):
  - yfinance returns absolute USD (e.g. 20,158,000,000 = US$20.16B).
  - In claim text, write "$20.16B" or "US$20.16B". DO NOT prefix with ₹.
  - In `EvidenceLink.values`, prefer USD billions (raw USD ÷ 1,000,000,000).
    Make the unit explicit in `metric`, e.g. "Revenue (USD B)".
  - Add a `data_quality_notes` entry calling out that yfinance reports this
    company in USD rather than INR.

Do NOT mix units within a single claim. If the claim mentions revenue and
debt, both use the same unit. Ratios (margins, ROE, ROCE, D/E, OCF/PAT) are
unitless or percentage and require no currency choice.
"""


def _build_yearly_data(snapshot: FinancialsSnapshot) -> list[YearlyDataPoint]:
    is_by = {y.period_end: y for y in snapshot.income_statement}
    bs_by = {y.period_end: y for y in snapshot.balance_sheet}
    cf_by = {y.period_end: y for y in snapshot.cash_flow}
    all_years = sorted(set(is_by) | set(bs_by) | set(cf_by), reverse=True)
    out: list[YearlyDataPoint] = []
    for year in all_years:
        inc = is_by.get(year)
        bs = bs_by.get(year)
        cf = cf_by.get(year)
        out.append(
            YearlyDataPoint(
                period_end=year,
                revenue=inc.revenue if inc else None,
                operating_income=inc.operating_income if inc else None,
                net_income=inc.net_income if inc else None,
                operating_cash_flow=cf.operating_cash_flow if cf else None,
                free_cash_flow=cf.free_cash_flow if cf else None,
                total_debt=bs.total_debt if bs else None,
                total_equity=bs.total_equity if bs else None,
            )
        )
    return out


def _build_agent() -> Agent[AgentDeps, FinancialsReport]:
    settings = get_settings()
    agent = Agent[AgentDeps, FinancialsReport](
        model=build_model(ModelTier.AGENT, settings),
        deps_type=AgentDeps,
        output_type=FinancialsReport,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.tool
    async def yfinance_fetch_financials(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> FinancialsSnapshot:
        """Fetch 5-year financials (income, balance, cash flow) from yfinance.

        Returns a FinancialsSnapshot. Use this tool exactly once per run.
        """
        log.info("agent.financials.tool.yfinance_fetch", ticker=ticker)
        return await ctx.deps.yfinance_client.fetch_financials(ticker)

    @agent.tool
    async def compute_ratios(ctx: RunContext[AgentDeps], ticker: str) -> RatiosTable:
        """Compute all key ratios deterministically in Python.

        Returns yearly ratios (margins, ROE, ROCE, leverage, liquidity, cash
        quality) and growth CAGRs. Internally re-fetches the yfinance snapshot
        from cache (fast). Use this tool's output verbatim — DO NOT compute
        ratios yourself.
        """
        log.info("agent.financials.tool.compute_ratios", ticker=ticker)
        snapshot = await ctx.deps.yfinance_client.fetch_financials(ticker)
        return _compute_ratios_pure(snapshot)

    @agent.tool
    async def screener_fetch_financials(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> ScreenerSnapshot:
        """Fetch supplementary financials from Screener.in.

        STEP 3 STATUS: Returns `available=false` until step 6 lands the
        scraper. If you receive `available=false`, ignore this tool's output
        and continue with yfinance data alone.
        """
        log.info("agent.financials.tool.screener_fetch", ticker=ticker)
        return await ctx.deps.screener_scraper.fetch_company(ticker)

    return agent


# Lazy construction so importing this module doesn't require ANTHROPIC_API_KEY.
_agent: Agent[AgentDeps, FinancialsReport] | None = None


def get_financials_agent() -> Agent[AgentDeps, FinancialsReport]:
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


async def run_financials_agent(ticker: str, deps: AgentDeps) -> FinancialsReport:
    """Run the agent and stamp post-processed fields on the result.

    The agent populates yearly_data / ratios / qualitative_assessment /
    data_quality_notes. We layer in the deterministic identity fields
    (ticker, yfinance_symbol, company_name, sector, industry, currency,
    period_summary, generated_at) here so the LLM doesn't drift on them.
    """
    agent = get_financials_agent()
    log.info("agent.financials.run.start", ticker=ticker)

    user_prompt = (
        f"Produce a FinancialsReport for ticker {ticker.upper()}. "
        "Follow the workflow exactly. Use compute_ratios for every numeric "
        "ratio you cite. Make every qualitative finding evidence-linked."
    )

    result = await agent.run(user_prompt, deps=deps)
    report = result.output

    # Refresh identity fields from the tool snapshot so they stay deterministic.
    snapshot = await deps.yfinance_client.fetch_financials(ticker)
    report = report.model_copy(
        update={
            "ticker": ticker.upper(),
            "yfinance_symbol": snapshot.yfinance_symbol,
            "company_name": snapshot.company_name,
            "sector": snapshot.sector,
            "industry": snapshot.industry,
            "currency": snapshot.currency,
            "yearly_data": _build_yearly_data(snapshot),
            "ratios": _compute_ratios_pure(snapshot),
            "generated_at": datetime.now(UTC),
        }
    )

    log.info(
        "agent.financials.run.done",
        ticker=ticker,
        findings=len(report.qualitative_assessment),
        notes=len(report.data_quality_notes),
    )
    return report
