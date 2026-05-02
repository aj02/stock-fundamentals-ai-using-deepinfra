"""Unit tests for the Financials Agent.

Uses PydanticAI's TestModel with a pre-built valid `FinancialsReport` passed
via `custom_output_args`. Default TestModel synthesis can't satisfy our
strict schema (min 4 findings, min evidence per finding, claim min length),
which is exactly what we want at runtime — but for unit tests we feed it a
valid output so we can verify the tool wiring + post-processing pipeline.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.models.test import TestModel

from app.agents.deps import AgentDeps
from app.agents.financials import get_financials_agent, run_financials_agent
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
    ScreenerSnapshot,
)


def _fake_snapshot() -> FinancialsSnapshot:
    return FinancialsSnapshot(
        ticker="TESTCO",
        yfinance_symbol="TESTCO.NS",
        exchange="NSE",
        company_name="Test Company Ltd",
        sector="Technology",
        industry="Information Technology Services",
        currency="INR",
        income_statement=[
            IncomeStatementYear(
                period_end=date(2026, 3, 31),
                revenue=1_000_000.0,
                gross_profit=300_000.0,
                operating_income=150_000.0,
                ebit=160_000.0,
                net_income=100_000.0,
                interest_expense=20_000.0,
                basic_eps=10.0,
                diluted_eps=9.9,
            ),
            IncomeStatementYear(
                period_end=date(2025, 3, 31),
                revenue=900_000.0,
                gross_profit=270_000.0,
                operating_income=135_000.0,
                ebit=144_000.0,
                net_income=88_000.0,
                interest_expense=18_000.0,
                basic_eps=8.8,
                diluted_eps=8.7,
            ),
        ],
        balance_sheet=[
            BalanceSheetYear(
                period_end=date(2026, 3, 31),
                total_assets=2_000_000.0,
                current_assets=500_000.0,
                total_liabilities=1_000_000.0,
                non_current_liabilities=600_000.0,
                current_liabilities=400_000.0,
                total_equity=500_000.0,
                total_debt=225_000.0,
                cash_and_equivalents=50_000.0,
                working_capital=100_000.0,
                invested_capital=725_000.0,
            ),
        ],
        cash_flow=[
            CashFlowYear(
                period_end=date(2026, 3, 31),
                operating_cash_flow=150_000.0,
                capex=-40_000.0,
                free_cash_flow=110_000.0,
                dividends_paid=-10_000.0,
            ),
        ],
        fetched_at=datetime.now(UTC),
    )


def _fake_screener() -> ScreenerSnapshot:
    return ScreenerSnapshot(
        ticker="TESTCO",
        available=False,
        note="stub",
        fetched_at=datetime.now(UTC),
    )


def _fake_deps() -> AgentDeps:
    yf_client = MagicMock()
    yf_client.fetch_financials = AsyncMock(return_value=_fake_snapshot())

    scraper = MagicMock()
    scraper.fetch_company = AsyncMock(return_value=_fake_screener())

    peers = MagicMock()
    peers.fetch = AsyncMock()

    ar = MagicMock()
    ar.fetch_and_extract = AsyncMock()

    return AgentDeps(
        settings=MagicMock(),
        cache=MagicMock(),
        yfinance_client=yf_client,
        screener_scraper=scraper,
        peers_service=peers,
        annual_report_service=ar,
    )


def _fake_llm_report() -> FinancialsReport:
    """A minimal valid FinancialsReport — fields that get overlaid in
    post-processing are intentionally set to 'WRONG' so the test can
    distinguish post-processed values from LLM-emitted values.
    """
    return FinancialsReport(
        ticker="WRONG",
        yfinance_symbol="WRONG.NS",
        company_name="Wrong Company",
        sector="Wrong Sector",
        industry="Wrong Industry",
        currency="USD",
        period_summary="FY22 to FY26",
        yearly_data=[],
        ratios=RatiosTable(yearly=[], growth=GrowthRates()),
        qualitative_assessment=[
            QualitativeFinding(
                claim=(
                    "Revenue grew from FY25 ₹900,000 to FY26 ₹1,000,000 "
                    "(11.1 percent year over year)."
                ),
                category="growth",
                evidence=[
                    EvidenceLink(
                        metric="Revenue (₹)",
                        years_referenced=[2025, 2026],
                        values=[900_000.0, 1_000_000.0],
                    )
                ],
            ),
            QualitativeFinding(
                claim=(
                    "Net margin held at 10.0 percent in FY26 against 9.8 "
                    "percent in FY25."
                ),
                category="profitability",
                evidence=[
                    EvidenceLink(
                        metric="Net margin (%)",
                        years_referenced=[2025, 2026],
                        values=[9.78, 10.0],
                    )
                ],
            ),
            QualitativeFinding(
                claim=(
                    "Debt to Equity sat at 0.45 in FY26 with total debt "
                    "₹225,000 against equity ₹500,000."
                ),
                category="leverage",
                evidence=[
                    EvidenceLink(
                        metric="Debt/Equity",
                        years_referenced=[2026],
                        values=[0.45],
                    )
                ],
            ),
            QualitativeFinding(
                claim=(
                    "Operating cash flow ₹150,000 exceeded reported PAT "
                    "₹100,000 in FY26 (OCF/PAT 1.5)."
                ),
                category="cash_generation",
                evidence=[
                    EvidenceLink(
                        metric="OCF/PAT",
                        years_referenced=[2026],
                        values=[1.5],
                    )
                ],
            ),
        ],
        data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )


async def test_agent_calls_all_three_tools_and_post_processes_identity_fields() -> None:
    deps = _fake_deps()
    agent = get_financials_agent()

    test_model = TestModel(
        custom_output_args=_fake_llm_report().model_dump(mode="json")
    )
    with agent.override(model=test_model):
        report = await run_financials_agent("TESTCO", deps=deps)

    # All tool wrappers were exercised at least once during the LLM run.
    deps.yfinance_client.fetch_financials.assert_awaited()
    deps.screener_scraper.fetch_company.assert_awaited()

    # Identity fields are overlaid from the snapshot post-LLM, so the LLM's
    # "WRONG"/"USD" values are replaced.
    assert report.ticker == "TESTCO"
    assert report.yfinance_symbol == "TESTCO.NS"
    assert report.company_name == "Test Company Ltd"
    assert report.sector == "Technology"
    assert report.currency == "INR"

    # Ratios are computed deterministically post-LLM.
    assert len(report.ratios.yearly) >= 1
    fy26 = report.ratios.yearly[0]
    assert fy26.period_end == date(2026, 3, 31)
    # 100k / 1M = 10% net margin.
    assert fy26.net_margin_pct is not None
    assert abs(fy26.net_margin_pct - 10.0) < 0.01
    # Debt/Equity = 225k / 500k = 0.45.
    assert fy26.debt_to_equity is not None
    assert abs(fy26.debt_to_equity - 0.45) < 0.001

    # Yearly data table is built post-LLM, with 2 years' worth of rows.
    assert len(report.yearly_data) == 2

    # Pydantic strictness held — 4 to 7 findings, every finding has evidence.
    assert 4 <= len(report.qualitative_assessment) <= 7
    for finding in report.qualitative_assessment:
        assert len(finding.evidence) >= 1
        for ev in finding.evidence:
            assert len(ev.values) == len(ev.years_referenced)


async def test_disclaimer_is_in_every_report() -> None:
    deps = _fake_deps()
    agent = get_financials_agent()
    test_model = TestModel(
        custom_output_args=_fake_llm_report().model_dump(mode="json")
    )
    with agent.override(model=test_model):
        report = await run_financials_agent("TESTCO", deps=deps)
    assert "investment advice" in report.disclaimer.lower()
