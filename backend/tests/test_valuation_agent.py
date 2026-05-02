"""Unit tests for the Valuation Agent.

Same TestModel pattern as test_financials_agent — feed a pre-built valid
ValuationReport via custom_output_args, then assert the tool wiring +
post-processing pipeline.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.models.test import TestModel

from app.agents.deps import AgentDeps
from app.agents.valuation import get_valuation_agent, run_valuation_agent
from app.schemas.agents import EvidenceLink, QualitativeFinding
from app.schemas.financials import (
    BalanceSheetYear,
    CashFlowYear,
    FinancialsSnapshot,
    IncomeStatementYear,
)
from app.schemas.valuation import (
    HistoricalMedians,
    HistoricalValuation,
    HistoricalValuationPoint,
    PeerComparison,
    ValuationMultiples,
    ValuationReport,
)


def _fake_snapshot() -> FinancialsSnapshot:
    return FinancialsSnapshot(
        ticker="TESTCO",
        yfinance_symbol="TESTCO.NS",
        exchange="NSE",
        company_name="Test Company Ltd",
        sector="Technology",
        industry="IT Services",
        currency="INR",
        income_statement=[
            IncomeStatementYear(
                period_end=date(2026, 3, 31),
                revenue=1_000_000.0,
                net_income=100_000.0,
                diluted_eps=10.0,
                diluted_shares=10_000.0,
            )
        ],
        balance_sheet=[
            BalanceSheetYear(
                period_end=date(2026, 3, 31),
                total_equity=500_000.0,
            )
        ],
        cash_flow=[CashFlowYear(period_end=date(2026, 3, 31))],
        fetched_at=datetime.now(UTC),
    )


def _fake_multiples() -> ValuationMultiples:
    return ValuationMultiples(
        current_price=200.0,
        market_cap=2_000_000.0,
        trailing_pe=20.0,
        forward_pe=18.0,
        price_to_book=4.0,
        ev_to_ebitda=12.0,
        dividend_yield_pct=0.5,
        fetched_at=datetime.now(UTC),
    )


def _fake_history_points() -> list[HistoricalValuationPoint]:
    return [
        HistoricalValuationPoint(
            period_end=date(2026, 3, 31),
            fy_end_close_price=200.0,
            eps_for_year=10.0,
            book_value_per_share=50.0,
            pe=20.0,
            pb=4.0,
        ),
        HistoricalValuationPoint(
            period_end=date(2025, 3, 31),
            fy_end_close_price=150.0,
            eps_for_year=8.0,
            book_value_per_share=40.0,
            pe=18.75,
            pb=3.75,
        ),
    ]


def _fake_peers() -> PeerComparison:
    return PeerComparison(available=False, peers=[], fetched_at=datetime.now(UTC))


def _fake_deps() -> AgentDeps:
    yf = MagicMock()
    yf.fetch_financials = AsyncMock(return_value=_fake_snapshot())
    yf.fetch_current_multiples = AsyncMock(return_value=_fake_multiples())
    yf.fetch_historical_valuation_points = AsyncMock(return_value=_fake_history_points())

    scraper = MagicMock()

    peers = MagicMock()
    peers.fetch = AsyncMock(return_value=_fake_peers())

    ar = MagicMock()
    ar.fetch_and_extract = AsyncMock()

    return AgentDeps(
        settings=MagicMock(),
        cache=MagicMock(),
        yfinance_client=yf,
        screener_scraper=scraper,
        peers_service=peers,
        annual_report_service=ar,
    )


def _fake_llm_report() -> ValuationReport:
    finding = QualitativeFinding(
        claim=(
            "Trailing P/E of 20.0 is 3.3 percent above the 2-year median of "
            "19.4, with FY26 marking the high of the available window."
        ),
        category="growth",  # category from schemas.agents finding categories
        evidence=[
            EvidenceLink(
                metric="Trailing P/E (×)",
                years_referenced=[2026],
                values=[20.0],
            )
        ],
    )
    return ValuationReport(
        ticker="WRONG",
        yfinance_symbol="WRONG.NS",
        company_name="Wrong",
        sector="Wrong",
        industry="Wrong",
        currency="USD",
        period_summary="FY25 to FY26",
        current_multiples=_fake_multiples(),
        historical_valuation=HistoricalValuation(
            yearly=_fake_history_points(),
            medians=HistoricalMedians(
                pe_median=19.375,
                pb_median=3.875,
                pe_min=18.75,
                pe_max=20.0,
                pb_min=3.75,
                pb_max=4.0,
                years_in_window=2,
            ),
        ),
        peer_comparison=_fake_peers(),
        qualitative_assessment=[finding] * 4,
        data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )


async def test_valuation_agent_calls_all_tools_and_post_processes() -> None:
    deps = _fake_deps()
    agent = get_valuation_agent()

    test_model = TestModel(
        custom_output_args=_fake_llm_report().model_dump(mode="json")
    )
    with agent.override(model=test_model):
        report = await run_valuation_agent("TESTCO", deps=deps)

    deps.yfinance_client.fetch_current_multiples.assert_awaited()
    deps.yfinance_client.fetch_historical_valuation_points.assert_awaited()
    deps.peers_service.fetch.assert_awaited()

    # Identity overlaid post-LLM (LLM emitted "WRONG"/"USD"; reality is INR/TESTCO).
    assert report.ticker == "TESTCO"
    assert report.yfinance_symbol == "TESTCO.NS"
    assert report.currency == "INR"

    # Historical valuation series + medians come from the deterministic recompute.
    assert report.historical_valuation.medians.pe_median is not None
    assert report.historical_valuation.medians.years_in_window == 2

    # Peer stub propagated.
    assert report.peer_comparison.available is False

    # Disclaimer in place.
    assert "investment advice" in report.disclaimer.lower()

    # Strict shape held.
    assert 4 <= len(report.qualitative_assessment) <= 7
    for finding in report.qualitative_assessment:
        assert len(finding.evidence) >= 1
