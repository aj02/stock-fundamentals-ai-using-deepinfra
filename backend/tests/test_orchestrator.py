"""Tests for the orchestrator's parallel-run + partial-failure behaviour.

We patch each `run_*_agent` to be a controllable stub so the orchestrator's
asyncio.gather logic + per-section unavailable handling is exercised
without touching Anthropic.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents import orchestrator as orch_module
from app.agents.deps import AgentDeps
from app.agents.events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    RunCompletedEvent,
    RunStartedEvent,
)
from app.schemas.agents import (
    EvidenceLink,
    FinancialsReport,
    GrowthRates,
    QualitativeFinding,
    RatiosTable,
)
from app.schemas.financials import (
    BalanceSheetYear,
    CashFlowYear,
    FinancialsSnapshot,
    IncomeStatementYear,
)
from app.schemas.management import ManagementReport
from app.schemas.risk import RiskReport
from app.schemas.thesis import InvestmentThesis, ThesisCitation, ThesisPoint
from app.schemas.valuation import (
    HistoricalMedians,
    HistoricalValuation,
    PeerComparison,
    ValuationMultiples,
    ValuationReport,
)


def _fake_deps() -> AgentDeps:
    yf = MagicMock()
    yf.fetch_financials = AsyncMock(
        return_value=FinancialsSnapshot(
            ticker="TESTCO",
            yfinance_symbol="TESTCO.NS",
            exchange="NSE",
            company_name="Test Company Ltd",
            currency="INR",
            income_statement=[IncomeStatementYear(period_end=date(2026, 3, 31))],
            balance_sheet=[BalanceSheetYear(period_end=date(2026, 3, 31))],
            cash_flow=[CashFlowYear(period_end=date(2026, 3, 31))],
            fetched_at=datetime.now(UTC),
        )
    )
    return AgentDeps(
        settings=MagicMock(),
        cache=MagicMock(),
        yfinance_client=yf,
        screener_scraper=MagicMock(),
        peers_service=MagicMock(),
        annual_report_service=MagicMock(),
    )


def _fake_finding() -> QualitativeFinding:
    return QualitativeFinding(
        claim=(
            "Revenue grew 6.4 percent CAGR from FY23 ₹8.78L cr to FY26 "
            "₹10.57L cr."
        ),
        category="growth",
        evidence=[
            EvidenceLink(
                metric="Revenue (₹ cr)",
                years_referenced=[2023, 2026],
                values=[877_835.0, 1_057_219.0],
            )
        ],
    )


def _fake_financials() -> FinancialsReport:
    return FinancialsReport(
        ticker="TESTCO", yfinance_symbol="TESTCO.NS", company_name="Test Company Ltd",
        sector="Energy", industry="Oil", currency="INR",
        period_summary="FY23 to FY26",
        yearly_data=[],
        ratios=RatiosTable(yearly=[], growth=GrowthRates()),
        qualitative_assessment=[_fake_finding()] * 4,
        data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )


def _fake_valuation() -> ValuationReport:
    return ValuationReport(
        ticker="TESTCO", yfinance_symbol="TESTCO.NS", company_name="Test Company Ltd",
        sector="Energy", industry="Oil", currency="INR",
        period_summary="FY23 to FY26",
        current_multiples=ValuationMultiples(fetched_at=datetime.now(UTC)),
        historical_valuation=HistoricalValuation(
            yearly=[],
            medians=HistoricalMedians(),
        ),
        peer_comparison=PeerComparison(available=False, fetched_at=datetime.now(UTC)),
        qualitative_assessment=[_fake_finding()] * 4,
        data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )


def _fake_thesis() -> InvestmentThesis:
    citation = ThesisCitation(
        source_agent="financials", finding_index=0,
        summary="Revenue grew at 6.4 percent CAGR FY23 to FY26.",
    )
    point = ThesisPoint(
        point=(
            "Revenue base expanded with mid-single-digit consistency, "
            "supported by Financials finding 0."
        ),
        citations=[citation],
    )
    return InvestmentThesis(
        ticker="TESTCO", company_name="Test Company Ltd",
        bull_case=[point, point],
        bear_case=[point, point],
        neutral_summary=(
            "The picture is mixed: top-line grew steadily while peer-relative "
            "valuation context is unavailable at this build step. Cash "
            "generation and balance-sheet leverage are visible from prior "
            "agents; risk and management commentary did not contribute."
        ),
        sections_unavailable=[],
        generated_at=datetime.now(UTC),
    )


async def test_run_analysis_full_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: all 4 parallel agents succeed, then thesis runs."""
    monkeypatch.setattr(orch_module, "run_financials_agent", AsyncMock(return_value=_fake_financials()))
    monkeypatch.setattr(orch_module, "run_valuation_agent", AsyncMock(return_value=_fake_valuation()))
    monkeypatch.setattr(orch_module, "run_management_agent", AsyncMock(return_value=ManagementReport(
        ticker="TESTCO", yfinance_symbol="TESTCO.NS", company_name="Test Company Ltd",
        mda_findings=[], governance_findings=[], data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )))
    monkeypatch.setattr(orch_module, "run_risk_agent", AsyncMock(return_value=RiskReport(
        ticker="TESTCO", yfinance_symbol="TESTCO.NS", company_name="Test Company Ltd",
        risks=[], data_quality_notes=[], generated_at=datetime.now(UTC),
    )))
    monkeypatch.setattr(orch_module, "run_thesis_agent", AsyncMock(return_value=_fake_thesis()))

    events: list = []
    report = await orch_module.run_analysis(
        run_id="rid-1", ticker="TESTCO", depth="full", deps=_fake_deps(), on_event=events.append,
    )

    assert report.status == "completed"
    assert report.financials is not None
    assert report.valuation is not None
    assert report.management is not None
    assert report.risk is not None
    assert report.thesis is not None
    assert report.unavailable_sections == []

    # Event types we expect at minimum.
    types = [type(e).__name__ for e in events]
    assert "RunStartedEvent" in types
    assert types.count("AgentCompletedEvent") == 4  # 4 parallel agents
    assert "ThesisCompletedEvent" in types
    assert types[-1] == "RunCompletedEvent"


async def test_run_analysis_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """One parallel agent fails — orchestrator records it as unavailable
    and proceeds with thesis on the survivors."""

    async def _explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("annual report PDF parse failed")

    monkeypatch.setattr(orch_module, "run_financials_agent", AsyncMock(return_value=_fake_financials()))
    monkeypatch.setattr(orch_module, "run_valuation_agent", AsyncMock(return_value=_fake_valuation()))
    monkeypatch.setattr(orch_module, "run_management_agent", _explode)
    monkeypatch.setattr(orch_module, "run_risk_agent", _explode)
    monkeypatch.setattr(orch_module, "run_thesis_agent", AsyncMock(return_value=_fake_thesis()))

    events: list = []
    report = await orch_module.run_analysis(
        run_id="rid-2", ticker="TESTCO", depth="full", deps=_fake_deps(), on_event=events.append,
    )

    assert report.status == "completed"  # at least Financials + Valuation + Thesis succeeded
    assert report.financials is not None
    assert report.valuation is not None
    assert report.management is None
    assert report.risk is None
    unavailable = {u.section for u in report.unavailable_sections}
    assert "management" in unavailable
    assert "risk" in unavailable
    assert "thesis" not in unavailable  # Thesis still ran on survivors

    types = [type(e).__name__ for e in events]
    assert types.count("AgentFailedEvent") >= 2


async def test_run_analysis_total_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """All parallel agents fail — orchestrator records the run as failed
    and skips the thesis (no survivors to synthesise from)."""

    async def _explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(orch_module, "run_financials_agent", _explode)
    monkeypatch.setattr(orch_module, "run_valuation_agent", _explode)
    monkeypatch.setattr(orch_module, "run_management_agent", _explode)
    monkeypatch.setattr(orch_module, "run_risk_agent", _explode)
    thesis_mock = AsyncMock(return_value=_fake_thesis())
    monkeypatch.setattr(orch_module, "run_thesis_agent", thesis_mock)

    events: list = []
    report = await orch_module.run_analysis(
        run_id="rid-3", ticker="TESTCO", depth="full", deps=_fake_deps(), on_event=events.append,
    )

    assert report.status == "failed"
    assert report.thesis is None
    thesis_mock.assert_not_called()  # never even attempted
    unavailable = {u.section for u in report.unavailable_sections}
    assert {"financials", "valuation", "management", "risk", "thesis"}.issubset(unavailable)


async def test_run_analysis_quick_skips_management_and_risk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Depth=quick attempts only Financials + Valuation, then Thesis."""
    monkeypatch.setattr(orch_module, "run_financials_agent", AsyncMock(return_value=_fake_financials()))
    monkeypatch.setattr(orch_module, "run_valuation_agent", AsyncMock(return_value=_fake_valuation()))
    mgmt_mock = AsyncMock()
    risk_mock = AsyncMock()
    monkeypatch.setattr(orch_module, "run_management_agent", mgmt_mock)
    monkeypatch.setattr(orch_module, "run_risk_agent", risk_mock)
    monkeypatch.setattr(orch_module, "run_thesis_agent", AsyncMock(return_value=_fake_thesis()))

    report = await orch_module.run_analysis(
        run_id="rid-4", ticker="TESTCO", depth="quick", deps=_fake_deps(), on_event=None,
    )

    assert report.status == "completed"
    assert report.management is None
    assert report.risk is None
    mgmt_mock.assert_not_called()
    risk_mock.assert_not_called()
    # Quick run does NOT mark management/risk as unavailable — they were never attempted.
    sections = {u.section for u in report.unavailable_sections}
    assert "management" not in sections
    assert "risk" not in sections
