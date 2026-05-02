"""Valuation Agent.

Compares current valuation multiples vs the company's own 5-year history
and (when peers are available) vs sector medians. Output is descriptive
("P/E is X% above the 4-year median"), never prescriptive (no "fair value",
no "undervalued/overvalued" verdict, no price target).

Tools:
  - yfinance_fetch_current_multiples — current P/E, P/B, EV/EBITDA, divyld, etc.
  - yfinance_fetch_historical_valuation — per-FY P/E and P/B series.
  - compute_historical_medians — pure-Python medians/min/max over the series.
  - peers_fetch — STUB until step 6; returns available=False.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic_ai import Agent, RunContext

from app.agents.deps import AgentDeps
from app.agents.llm import ModelTier, build_model
from app.core.config import get_settings
from app.schemas.valuation import (
    HistoricalMedians,
    HistoricalValuation,
    HistoricalValuationPoint,
    PeerComparison,
    ValuationMultiples,
    ValuationReport,
)
from app.services.valuation import compute_medians as _compute_medians

log = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are a valuation analyst for an Indian listed company (NSE/BSE). You will
compare the company's CURRENT valuation multiples against its OWN history,
and against peers when peer data is available.

═══════════════════════════════════════════════════════════════════════════
WORKFLOW (follow exactly)
═══════════════════════════════════════════════════════════════════════════
1. Call `yfinance_fetch_current_multiples(ticker)` — current price, market
   cap, EV, P/E (trailing + forward), P/B, P/S, EV/EBITDA, EV/Revenue,
   dividend yield, payout ratio, 52-week range, EPS, book value/share.
2. Call `yfinance_fetch_historical_valuation(ticker)` — per-fiscal-year
   close × EPS / book value, producing P/E and P/B for each year of history.
3. Call `compute_historical_medians(ticker)` — deterministic medians,
   min, max across the historical series. Use this tool's output verbatim.
   DO NOT compute medians yourself.
4. Call `peers_fetch(ticker)`. If `available: false`, IGNORE the peer
   comparison and note in `data_quality_notes` that peer data is unavailable
   at this build step.

═══════════════════════════════════════════════════════════════════════════
QUALITATIVE ASSESSMENT — STRICT RULES
═══════════════════════════════════════════════════════════════════════════
- Produce 4–7 findings. Each finding 1–2 sentences max.
- Cover at least three of: current_vs_history, pe_trajectory, pb_trajectory,
  dividend_policy, ev_multiples, peer_comparison (peer_comparison only if
  peers are actually available).
- EVERY claim cites specific multiples with their year(s) in plain English,
  e.g. "Trailing P/E of 24.1× is 14% above the 4-year median of 21.2×
  (range 18.5×–25.7× across FY23–FY26)".
- EVERY finding includes at least one EvidenceLink with metric name, years,
  and values.

────── BANNED PHRASES — do not use any of these ──────
"undervalued", "overvalued", "cheap", "expensive", "attractive",
"fair value", "intrinsic value", "value buy", "growth at a reasonable price",
"GARP", "stock looks", "stock appears", "good entry point", "attractive entry",
"strong fundamentals", "robust", "solid", "healthy", "good", "great",
"impressive", "best-in-class", "market leader", "industry leader", "premier",
"compelling", "high quality", "should outperform", "should re-rate",
"should compress", "trades at a discount", "trades at a premium" (unless
literally citing the percentage and the comparison anchor).

If you find yourself reaching for one of these, STOP. State the comparison
factually: "P/E of X is Y% above/below the Z-year median of M".

────── DESCRIPTIVE ONLY — do NOT do these ──────
- Do NOT recommend buying, selling, or holding.
- Do NOT assign a numeric score, rating, or grade.
- Do NOT give a "fair value" or price target.
- Do NOT speculate about future stock price direction.
- Do NOT compare valuation to "growth potential" or "intrinsic value".

═══════════════════════════════════════════════════════════════════════════
EVIDENCE EXAMPLES
═══════════════════════════════════════════════════════════════════════════

GOOD finding (specific, factual, no verdict):
{
  "claim": "Trailing P/E of 24.1× sits 13% above the 4-year median of 21.4× \
(range 18.7× in FY24 to 25.7× in FY26), with the FY26 multiple being the \
highest in the available window.",
  "category": "current_vs_history",
  "evidence": [
    {"metric": "Trailing P/E (×)", "years_referenced": [2026], "values": [24.07]},
    {"metric": "Median P/E (4Y) (×)", "years_referenced": [2023, 2026], "values": [21.4]},
    {"metric": "Historical P/E (×)", "years_referenced": [2023, 2024, 2025, 2026],
     "values": [22.1, 18.7, 19.5, 25.7]}
  ]
}

BAD finding (verdict-laden, banned vocabulary — DO NOT EMIT):
{
  "claim": "The stock looks expensive at current levels and may not offer \
attractive entry given strong fundamentals are already priced in.",
  "category": "current_vs_history",
  ...
}

═══════════════════════════════════════════════════════════════════════════
DATA QUALITY
═══════════════════════════════════════════════════════════════════════════
- If P/E history is dense at the long end but sparse most recently (e.g.
  EPS missing for FY26), say so in `data_quality_notes`.
- If forward P/E is much lower than trailing P/E, that means analyst-
  consensus EPS is well above trailing — note it factually.
- Negative-EPS years yield meaningless P/E. The historical series filters
  these out; if more than half the window had negative EPS, note it.
- Peer data unavailable at step 5 — explicitly note this.

═══════════════════════════════════════════════════════════════════════════
CURRENCY
═══════════════════════════════════════════════════════════════════════════
Multiples are unitless or percentages. Prices and book values use the
currency on the snapshot. For Infosys-like USD-reporting companies, write
"$X" not "₹X". For most companies, INR; quote prices in ₹.
"""


def _build_agent() -> Agent[AgentDeps, ValuationReport]:
    settings = get_settings()
    agent = Agent[AgentDeps, ValuationReport](
        model=build_model(ModelTier.AGENT, settings),
        deps_type=AgentDeps,
        output_type=ValuationReport,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.tool
    async def yfinance_fetch_current_multiples(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> ValuationMultiples:
        """Fetch current valuation multiples (P/E, P/B, EV/EBITDA, divyld, etc.)."""
        log.info("agent.valuation.tool.current_multiples", ticker=ticker)
        return await ctx.deps.yfinance_client.fetch_current_multiples(ticker)

    @agent.tool
    async def yfinance_fetch_historical_valuation(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> list[HistoricalValuationPoint]:
        """Fetch per-fiscal-year P/E and P/B series.

        Combines monthly close prices around each FY-end with diluted EPS
        and book value per share from the financials snapshot. Returns a
        list newest-first.
        """
        log.info("agent.valuation.tool.historical_valuation", ticker=ticker)
        return await ctx.deps.yfinance_client.fetch_historical_valuation_points(ticker)

    @agent.tool
    async def compute_historical_medians(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> HistoricalMedians:
        """Median, min, max P/E and P/B across the available history.

        Computed deterministically in Python — use this tool's output
        verbatim instead of computing medians yourself.
        """
        log.info("agent.valuation.tool.compute_medians", ticker=ticker)
        points = await ctx.deps.yfinance_client.fetch_historical_valuation_points(ticker)
        return _compute_medians(points)

    @agent.tool
    async def peers_fetch(
        ctx: RunContext[AgentDeps], ticker: str
    ) -> PeerComparison:
        """Fetch sector / industry peers + their multiples.

        STEP 5 STATUS: Returns `available=false`. Real peer lookup ships
        with the Screener.in scraper at step 6. If `available=false`,
        skip the peer-comparison finding category and note unavailability
        in `data_quality_notes`.
        """
        log.info("agent.valuation.tool.peers_fetch", ticker=ticker)
        return await ctx.deps.peers_service.fetch(ticker)

    return agent


_agent: Agent[AgentDeps, ValuationReport] | None = None


def get_valuation_agent() -> Agent[AgentDeps, ValuationReport]:
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


async def run_valuation_agent(ticker: str, deps: AgentDeps) -> ValuationReport:
    agent = get_valuation_agent()
    log.info("agent.valuation.run.start", ticker=ticker)

    user_prompt = (
        f"Produce a ValuationReport for ticker {ticker.upper()}. "
        "Follow the workflow exactly. Use compute_historical_medians for any "
        "median you cite. Make every qualitative finding evidence-linked and "
        "purely factual — no verdicts."
    )

    result = await agent.run(user_prompt, deps=deps)
    report = result.output

    # Overlay deterministic identity + recomputed series so the LLM can't
    # drift on the numbers themselves.
    snapshot = await deps.yfinance_client.fetch_financials(ticker)
    multiples = await deps.yfinance_client.fetch_current_multiples(ticker)
    points = await deps.yfinance_client.fetch_historical_valuation_points(ticker)
    historical = HistoricalValuation(
        yearly=sorted(points, key=lambda p: p.period_end, reverse=True),
        medians=_compute_medians(points),
    )
    peers = await deps.peers_service.fetch(ticker)

    report = report.model_copy(
        update={
            "ticker": ticker.upper(),
            "yfinance_symbol": snapshot.yfinance_symbol,
            "company_name": snapshot.company_name,
            "sector": snapshot.sector,
            "industry": snapshot.industry,
            "currency": snapshot.currency,
            "current_multiples": multiples,
            "historical_valuation": historical,
            "peer_comparison": peers,
            "generated_at": datetime.now(UTC),
        }
    )

    log.info(
        "agent.valuation.run.done",
        ticker=ticker,
        findings=len(report.qualitative_assessment),
        history_years=historical.medians.years_in_window,
        peers_available=peers.available,
    )
    return report
