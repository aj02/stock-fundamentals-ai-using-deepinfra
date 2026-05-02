"""Tests for the Thesis Agent — TestModel + custom_output_args.

We feed a pre-built valid `InvestmentThesis` so the strict citation
shape (every bull/bear point cites at least one prior agent) doesn't
trip the TestModel synth output.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.models.test import TestModel

from app.agents.deps import AgentDeps
from app.agents.thesis import (
    _summarise_findings_for_prompt,
    get_thesis_agent,
    run_thesis_agent,
)
from app.schemas.agents import (
    EvidenceLink,
    FinancialsReport,
    GrowthRates,
    QualitativeFinding,
    RatiosTable,
)
from app.schemas.management import ManagementFinding, ManagementReport, TextEvidence
from app.schemas.risk import RiskEvidence, RiskFinding, RiskReport
from app.schemas.thesis import (
    InvestmentThesis,
    ThesisCitation,
    ThesisPoint,
)
from app.schemas.valuation import (
    HistoricalMedians,
    HistoricalValuation,
    PeerComparison,
    ValuationMultiples,
    ValuationReport,
)


def _qf(claim: str, category: str = "growth") -> QualitativeFinding:
    return QualitativeFinding(
        claim=claim,
        category=category,  # type: ignore[arg-type]
        evidence=[
            EvidenceLink(metric="X", years_referenced=[2026], values=[1.0])
        ],
    )


def _fin() -> FinancialsReport:
    return FinancialsReport(
        ticker="T", yfinance_symbol="T.NS",
        currency="INR", period_summary="…",
        yearly_data=[],
        ratios=RatiosTable(yearly=[], growth=GrowthRates()),
        qualitative_assessment=[
            _qf("Revenue grew at 6.4 percent CAGR from FY23 to FY26."),
            _qf("Operating margin held in a 11.5-12.4 percent band.", category="profitability"),
            _qf("Debt-to-equity declined from 0.47 to 0.44.", category="leverage"),
            _qf("OCF/PAT averaged 2.24x over four years.", category="earnings_quality"),
        ],
        data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )


def _val() -> ValuationReport:
    return ValuationReport(
        ticker="T", yfinance_symbol="T.NS",
        currency="INR", period_summary="…",
        current_multiples=ValuationMultiples(fetched_at=datetime.now(UTC)),
        historical_valuation=HistoricalValuation(yearly=[], medians=HistoricalMedians()),
        peer_comparison=PeerComparison(available=False, fetched_at=datetime.now(UTC)),
        qualitative_assessment=[
            _qf("Trailing P/E sits 5.6 percent below 4-year median of 25.5x.", category="other"),
            _qf("Forward P/E is 17.4 percent below trailing.", category="growth"),
            _qf("EV exceeds market cap by 17 percent.", category="leverage"),
            _qf("Dividend yield is 0.38 percent.", category="profitability"),
        ],
        data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )


def _fake_deps() -> AgentDeps:
    return AgentDeps(
        settings=MagicMock(), cache=MagicMock(),
        yfinance_client=MagicMock(), screener_scraper=MagicMock(),
        peers_service=MagicMock(), annual_report_service=MagicMock(),
    )


def _fake_thesis_output() -> InvestmentThesis:
    bull = ThesisPoint(
        point=(
            "Cash generation is durable: OCF/PAT averaged 2.24x and revenue "
            "grew at 6.4 percent CAGR over four years."
        ),
        citations=[
            ThesisCitation(source_agent="financials", finding_index=3,
                           summary="OCF/PAT averaged 2.24x over four years."),
            ThesisCitation(source_agent="financials", finding_index=0,
                           summary="Revenue grew at 6.4 percent CAGR FY23 to FY26."),
        ],
    )
    bear = ThesisPoint(
        point=(
            "Margin and capital-efficiency drift: operating margin held in "
            "a 11.5 to 12.4 percent band while D/E declined modestly."
        ),
        citations=[
            ThesisCitation(source_agent="financials", finding_index=1,
                           summary="Operating margin band of 11.5-12.4 percent."),
        ],
    )
    return InvestmentThesis(
        ticker="T", company_name=None,
        bull_case=[bull, bull],
        bear_case=[bear, bear],
        neutral_summary=(
            "The picture combines mid-single-digit revenue growth with "
            "stable margins and improving cash generation. Valuation sits "
            "below the company's own 4-year median. Peer comparison is "
            "unavailable at this build step."
        ),
        sections_unavailable=[],
        generated_at=datetime.now(UTC),
    )


async def test_thesis_agent_post_processes_identity() -> None:
    deps = _fake_deps()
    agent = get_thesis_agent()

    test_model = TestModel(custom_output_args=_fake_thesis_output().model_dump(mode="json"))
    with agent.override(model=test_model):
        thesis = await run_thesis_agent(
            "TESTCO", deps, fin=_fin(), val=_val(), mgmt=None, risk=None,
        )

    assert thesis.ticker == "TESTCO"
    # Sections that weren't attempted should be in sections_unavailable.
    assert "management" in thesis.sections_unavailable
    assert "risk" in thesis.sections_unavailable
    # bull/bear/neutral all populated and citations resolve to indices we
    # actually presented in the prompt.
    assert 2 <= len(thesis.bull_case) <= 6
    assert 2 <= len(thesis.bear_case) <= 6
    for p in thesis.bull_case + thesis.bear_case:
        for c in p.citations:
            assert c.source_agent in ("financials", "valuation", "management", "risk")


def test_summarise_prompt_includes_indices() -> None:
    text, unavailable = _summarise_findings_for_prompt(
        fin=_fin(), val=_val(), mgmt=None, risk=None,
    )
    assert "FINANCIALS findings (4):" in text
    assert "  [0] (growth)" in text
    assert "  [3] (earnings_quality)" in text
    assert "VALUATION findings (4):" in text
    assert "MANAGEMENT findings: <UNAVAILABLE>" in text
    assert "RISK findings: <UNAVAILABLE>" in text
    assert unavailable == ["management", "risk"]
