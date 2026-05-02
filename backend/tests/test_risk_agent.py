"""Unit test for the Risk Agent — TestModel + custom_output_args."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.models.test import TestModel

from app.agents.deps import AgentDeps
from app.agents.risk import get_risk_agent, run_risk_agent
from app.schemas.annual_report import AnnualReportSection, AnnualReportSnapshot
from app.schemas.financials import (
    BalanceSheetYear,
    CashFlowYear,
    FinancialsSnapshot,
    IncomeStatementYear,
    ScreenerSnapshot,
)
from app.schemas.risk import RiskEvidence, RiskFinding, RiskReport


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
            IncomeStatementYear(period_end=date(2026, 3, 31), revenue=1.0)
        ],
        balance_sheet=[BalanceSheetYear(period_end=date(2026, 3, 31))],
        cash_flow=[CashFlowYear(period_end=date(2026, 3, 31))],
        fetched_at=datetime.now(UTC),
    )


def _fake_screener() -> ScreenerSnapshot:
    return ScreenerSnapshot(
        ticker="TESTCO",
        available=True,
        company_name="Test Company Ltd",
        pros=[],
        cons=[
            "Company has a low return on equity of 8.91% over last 3 years.",
            "Dividend payout has been low at 10.2% of profits over last 3 years",
        ],
        annual_reports=[],
        source_url="https://example/screener",
        fetched_at=datetime.now(UTC),
    )


def _fake_ar() -> AnnualReportSnapshot:
    return AnnualReportSnapshot(
        ticker="TESTCO",
        available=True,
        fiscal_year=2025,
        source_url="https://example/ar.pdf",
        page_count=200,
        sections={
            "risks": AnnualReportSection(
                section_type="risks",
                heading_found="Risk Management Framework",
                page_start=120,
                page_end=130,
                text=(
                    "Principal risks identified include commodity price "
                    "volatility, regulatory changes in licensing, and "
                    "currency translation on USD-denominated debt of "
                    "USD 8.5 billion as at 31 March 2025."
                ),
                word_count=30,
                truncated=False,
            )
        },
        fetched_at=datetime.now(UTC),
    )


def _fake_deps() -> AgentDeps:
    yf = MagicMock()
    yf.fetch_financials = AsyncMock(return_value=_fake_snapshot())

    scraper = MagicMock()
    scraper.fetch_company = AsyncMock(return_value=_fake_screener())

    peers = MagicMock()
    peers.fetch = AsyncMock()

    ar = MagicMock()
    ar.fetch_and_extract = AsyncMock(return_value=_fake_ar())

    return AgentDeps(
        settings=MagicMock(),
        cache=MagicMock(),
        yfinance_client=yf,
        screener_scraper=scraper,
        peers_service=peers,
        annual_report_service=ar,
    )


def _fake_llm_report() -> RiskReport:
    return RiskReport(
        ticker="WRONG",
        yfinance_symbol="WRONG.NS",
        company_name="Wrong",
        fiscal_year=2024,
        annual_report_url="https://wrong/ar.pdf",
        risks=[
            RiskFinding(
                risk=(
                    "Currency translation risk on USD 8.5 billion of USD-"
                    "denominated debt against an INR functional currency."
                ),
                category="financial",
                severity="medium",
                mitigation_summary=None,
                evidence=[
                    RiskEvidence(
                        quote=(
                            "currency translation on USD-denominated debt of "
                            "USD 8.5 billion as at 31 March 2025."
                        ),
                        source="annual_report",
                        section="risks",
                        page=120,
                    )
                ],
            ),
            RiskFinding(
                risk=(
                    "Sustained low return on equity averaging 8.91% over the "
                    "last three years, suggesting limited returns on capital."
                ),
                category="financial",
                severity="medium",
                mitigation_summary=None,
                evidence=[
                    RiskEvidence(
                        quote="Company has a low return on equity of 8.91% over last 3 years.",
                        source="screener_concern",
                        section=None,
                    )
                ],
            ),
        ],
        screener_concerns_used=True,
        data_quality_notes=[],
        generated_at=datetime.now(UTC),
    )


async def test_risk_agent_calls_both_tools_and_post_processes() -> None:
    deps = _fake_deps()
    agent = get_risk_agent()

    test_model = TestModel(
        custom_output_args=_fake_llm_report().model_dump(mode="json")
    )
    with agent.override(model=test_model):
        report = await run_risk_agent("TESTCO", deps=deps)

    deps.annual_report_service.fetch_and_extract.assert_awaited()
    deps.screener_scraper.fetch_company.assert_awaited()

    # Identity overlaid post-LLM.
    assert report.ticker == "TESTCO"
    assert report.yfinance_symbol == "TESTCO.NS"
    assert report.company_name == "Test Company Ltd"
    assert report.fiscal_year == 2025

    # Risks list validates and preserves structure.
    assert len(report.risks) == 2
    for r in report.risks:
        assert len(r.evidence) >= 1
        for ev in r.evidence:
            assert len(ev.quote) >= 20

    # Disclaimer in place.
    assert "investment advice" in report.disclaimer.lower()
