"""Thesis Agent — pure synthesis, NO tools.

Receives compact summaries of the 4 prior agents' findings as part of the
user prompt and produces a bull/bear/neutral synthesis. Every bull or
bear point MUST cite which prior finding it derives from (by source agent
+ finding index). This makes the synthesis auditable end-to-end.

Critical design choice (per spec): the Thesis Agent has NO tools. All
information is in the prompt. This forces it to synthesise rather than
re-fetch, and prevents it from making up numbers we didn't already
compute deterministically.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic_ai import Agent

from app.agents.deps import AgentDeps
from app.agents.llm import ModelTier, build_model
from app.core.config import get_settings
from app.schemas.agents import FinancialsReport, QualitativeFinding
from app.schemas.management import ManagementReport
from app.schemas.risk import RiskReport
from app.schemas.thesis import InvestmentThesis, ThesisSourceAgent
from app.schemas.valuation import ValuationReport

log = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are an investment-thesis analyst. You will receive four prior reports
covering Financials, Valuation, Management, and Risk for an Indian listed
company, and you will produce an `InvestmentThesis`: 2–6 bull points, 2–6
bear points, and a 2–4 sentence neutral synthesis.

═══════════════════════════════════════════════════════════════════════════
THE INPUT
═══════════════════════════════════════════════════════════════════════════
The user prompt will contain four sections, each listing the agent's
findings with explicit indices like:

  FINANCIALS findings (4):
    [0] (growth) Revenue grew at 6.4% CAGR from FY23 ₹8.78L cr to FY26 ₹10.57L cr.
    [1] (profitability) Gross margin expanded from 23.5% in FY23 to 29.4% in FY26.
    ...

When you cite a finding in `ThesisCitation`, use these indices as
`finding_index` (e.g. `{"source_agent": "financials", "finding_index": 0}`).
Do NOT renumber. Do NOT guess. Use ONLY indices that appear in the prompt.

If an agent's section is missing (`<UNAVAILABLE>`), record it in
`sections_unavailable` and DO NOT cite it.

═══════════════════════════════════════════════════════════════════════════
RULES — STRICT
═══════════════════════════════════════════════════════════════════════════
- EVERY bull or bear point MUST have at least one ThesisCitation. No
  uncited points.
- Each citation MUST point to a real finding index that's actually in the
  prompt. Inventing index 5 when only 4 findings exist is forbidden.
- The `summary` inside each citation must be a one-sentence reminder of
  what the cited finding said — not a paraphrase, not an embellishment.
- Cover both upside and downside angles drawing from MULTIPLE source
  agents. A thesis that draws ALL bull points from Financials and ALL
  bear points from Risk is shallow — try to weave at least 2 source
  agents per side.
- Frame bull/bear points as STATEMENTS OF FACT plus their implication,
  not as recommendations. "OCF consistently exceeds PAT, suggesting high
  earnings quality" is OK. "This is a buy" is NOT.

────── BANNED PHRASES ──────
"strong fundamentals", "robust", "solid", "healthy", "great",
"impressive", "best-in-class", "market leader", "industry leader",
"premier", "compelling", "high quality" (in the bare sense — quoting a
prior finding's text containing this word is OK if you cite it),
"undervalued", "overvalued", "cheap", "expensive", "attractive entry",
"fair value", "intrinsic value", "buy", "sell", "hold", "should
outperform", "we believe", "we expect", "in our view".

If reaching for one of these, STOP. State the specific number and source.

────── DESCRIPTIVE ONLY ──────
- NO buy / sell / hold / accumulate / book profits language.
- NO numeric score, rating, or grade.
- NO price target, "fair value", or implied target.
- NO comparison to peers unless the Valuation report's peer_comparison
  section was actually available (it usually isn't yet — the stub
  returns available=False).

═══════════════════════════════════════════════════════════════════════════
EVIDENCE EXAMPLES
═══════════════════════════════════════════════════════════════════════════

GOOD bull point (specific, multi-cited, no verdict):
{
  "point": "Earnings quality has been consistently high — OCF/PAT averaged \
2.24× across FY23-FY26 with FCF turning sharply positive after capex \
peaked in FY24, supporting the case that reported profits are backed by \
cash.",
  "citations": [
    {"source_agent": "financials", "finding_index": 3,
     "summary": "OCF exceeded PAT every year FY23-FY26, averaging 2.24x."},
    {"source_agent": "financials", "finding_index": 4,
     "summary": "FCF rose from -₹25,956 cr in FY23 to +₹69,197 cr in FY26."}
  ]
}

GOOD bear point (multi-source, factual):
{
  "point": "Trailing P/E of 24.1× sits 5.6% below the 4-year median while \
ROE has compressed to 8.93% (FY26) from 9.32% (FY23) — the multiple is \
not particularly elevated, but capital efficiency is drifting against \
an expanding equity base.",
  "citations": [
    {"source_agent": "valuation", "finding_index": 0,
     "summary": "Trailing P/E 24.1x vs 5y median 25.5x."},
    {"source_agent": "financials", "finding_index": 5,
     "summary": "ROE moved 9.32% (FY23) -> 8.93% (FY26) on growing equity base."}
  ]
}

BAD bull point (no citation, banned vocab — DO NOT EMIT):
{
  "point": "The company has strong fundamentals and is a market leader \
poised for growth.",
  "citations": []
}

═══════════════════════════════════════════════════════════════════════════
NEUTRAL SUMMARY
═══════════════════════════════════════════════════════════════════════════
2–4 sentences that JOINTLY describe what the four reports say. Avoid
hedging language like "should be considered" — describe the picture
factually. The neutral_summary is intentionally short; bull/bear capture
the directional reads.

═══════════════════════════════════════════════════════════════════════════
SECTIONS_UNAVAILABLE
═══════════════════════════════════════════════════════════════════════════
If a prior agent's section was marked `<UNAVAILABLE>` in the prompt,
add its name to `sections_unavailable`. The bull/bear case still works
from whatever sections DID succeed — degrade gracefully.
"""


def _summarise_findings_for_prompt(
    fin: FinancialsReport | None,
    val: ValuationReport | None,
    mgmt: ManagementReport | None,
    risk: RiskReport | None,
) -> tuple[str, list[ThesisSourceAgent]]:
    """Build the user prompt the Thesis Agent will read.

    For each available agent we list its findings with an explicit numeric
    index. Index numbering is what the Thesis Agent must use in
    ThesisCitation.finding_index — keep it zero-based and dense.
    """
    unavailable: list[ThesisSourceAgent] = []
    parts: list[str] = []

    def _qf_block(label: str, agent_key: ThesisSourceAgent, findings: list[QualitativeFinding] | None) -> None:
        if findings is None or len(findings) == 0:
            unavailable.append(agent_key)
            parts.append(f"{label} findings: <UNAVAILABLE>")
            return
        lines = [f"{label} findings ({len(findings)}):"]
        for i, f in enumerate(findings):
            lines.append(f"  [{i}] ({f.category}) {f.claim}")
        parts.append("\n".join(lines))

    _qf_block("FINANCIALS", "financials", fin.qualitative_assessment if fin else None)
    _qf_block("VALUATION", "valuation", val.qualitative_assessment if val else None)

    # Management has split lists — flatten to a single ordered list with
    # explicit "MDA-N" / "GOV-N" prefix in the printed line. We still use
    # 0..len-1 numbering for citations.
    if mgmt is not None and (mgmt.mda_findings or mgmt.governance_findings):
        combined = list(mgmt.mda_findings) + list(mgmt.governance_findings)
        boundary = len(mgmt.mda_findings)
        lines = [f"MANAGEMENT findings ({len(combined)}):"]
        for i, f in enumerate(combined):
            origin = "MDA" if i < boundary else "GOV"
            quote_excerpt = f.evidence[0].quote[:120].rstrip() if f.evidence else ""
            lines.append(f"  [{i}] ({f.category}/{origin}) {f.claim}  // quote: \"{quote_excerpt}…\"")
        parts.append("\n".join(lines))
    else:
        unavailable.append("management")
        parts.append("MANAGEMENT findings: <UNAVAILABLE>")

    if risk is not None and risk.risks:
        lines = [f"RISK findings ({len(risk.risks)}):"]
        for i, r in enumerate(risk.risks):
            lines.append(f"  [{i}] ({r.category}/{r.severity}) {r.risk}")
        parts.append("\n".join(lines))
    else:
        unavailable.append("risk")
        parts.append("RISK findings: <UNAVAILABLE>")

    return "\n\n".join(parts), unavailable


def _build_agent() -> Agent[AgentDeps, InvestmentThesis]:
    settings = get_settings()
    return Agent[AgentDeps, InvestmentThesis](
        model=build_model(ModelTier.AGENT, settings),
        deps_type=AgentDeps,
        output_type=InvestmentThesis,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )


_agent: Agent[AgentDeps, InvestmentThesis] | None = None


def get_thesis_agent() -> Agent[AgentDeps, InvestmentThesis]:
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


async def run_thesis_agent(
    ticker: str,
    deps: AgentDeps,
    *,
    fin: FinancialsReport | None,
    val: ValuationReport | None,
    mgmt: ManagementReport | None,
    risk: RiskReport | None,
) -> InvestmentThesis:
    if all(x is None for x in (fin, val, mgmt, risk)):
        raise ValueError("Thesis Agent needs at least one prior agent's output")

    agent = get_thesis_agent()
    log.info("agent.thesis.run.start", ticker=ticker)

    findings_block, unavailable = _summarise_findings_for_prompt(fin, val, mgmt, risk)
    user_prompt = (
        f"Produce an InvestmentThesis for {ticker.upper()}.\n\n"
        "Below are the prior agents' findings with explicit indices. Cite "
        "EVERY bull/bear point against at least one of these — use the "
        "exact (source_agent, finding_index) pairs shown. If a section is "
        "marked <UNAVAILABLE>, list it in sections_unavailable and do NOT "
        "cite from it.\n\n"
        f"{findings_block}"
    )

    result = await agent.run(user_prompt, deps=deps)
    thesis = result.output

    company_name = (
        (fin.company_name if fin else None)
        or (val.company_name if val else None)
        or (mgmt.company_name if mgmt else None)
        or (risk.company_name if risk else None)
    )

    thesis = thesis.model_copy(
        update={
            "ticker": ticker.upper(),
            "company_name": company_name,
            "sections_unavailable": unavailable,
            "generated_at": datetime.now(UTC),
        }
    )

    log.info(
        "agent.thesis.run.done",
        ticker=ticker,
        bull_points=len(thesis.bull_case),
        bear_points=len(thesis.bear_case),
        unavailable=unavailable,
    )
    return thesis
