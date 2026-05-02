"""Unit tests for the pure-Python ratio computation.

These tests use synthetic FinancialsSnapshots so we can pin every output
value precisely. No yfinance, no mocking, no LLM.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.schemas.financials import (
    BalanceSheetYear,
    CashFlowYear,
    FinancialsSnapshot,
    IncomeStatementYear,
)
from app.services.ratios import compute_ratios


def _snapshot(years: int = 5) -> FinancialsSnapshot:
    """Build a clean 5-year (FY22 through FY26) snapshot with stable growth."""
    income = []
    balance = []
    cashflow = []
    base_revenue = 100_000.0
    base_ni = 10_000.0
    base_equity = 50_000.0
    for i in range(years):
        # i=0 → newest (FY26)
        period = date(2026 - i, 3, 31)
        # 10% YoY growth in revenue, 12% in NI; older years are smaller.
        revenue = base_revenue / (1.10**i)
        net_income = base_ni / (1.12**i)
        equity = base_equity / (1.08**i)
        income.append(
            IncomeStatementYear(
                period_end=period,
                revenue=revenue,
                gross_profit=revenue * 0.30,
                operating_income=revenue * 0.15,
                ebit=revenue * 0.16,
                net_income=net_income,
                interest_expense=revenue * 0.02,
                basic_eps=net_income / 1000,
                diluted_eps=net_income / 1000,
                diluted_shares=1000.0,
            )
        )
        balance.append(
            BalanceSheetYear(
                period_end=period,
                total_assets=equity * 2.0,
                current_assets=equity * 0.5,
                total_liabilities=equity * 1.0,
                non_current_liabilities=equity * 0.6,
                current_liabilities=equity * 0.4,
                total_equity=equity,
                total_debt=equity * 0.45,
                cash_and_equivalents=equity * 0.1,
                working_capital=equity * 0.1,
                invested_capital=equity * 1.45,
            )
        )
        cashflow.append(
            CashFlowYear(
                period_end=period,
                operating_cash_flow=net_income * 1.5,
                capex=-net_income * 0.4,
                free_cash_flow=net_income * 1.1,
                dividends_paid=-net_income * 0.1,
            )
        )
    return FinancialsSnapshot(
        ticker="TEST",
        yfinance_symbol="TEST.NS",
        exchange="NSE",
        income_statement=income,
        balance_sheet=balance,
        cash_flow=cashflow,
        fetched_at=datetime.now(UTC),
    )


def test_yearly_ratios_are_computed_for_every_year() -> None:
    snap = _snapshot(years=5)
    table = compute_ratios(snap)
    assert len(table.yearly) == 5
    # Newest first.
    assert table.yearly[0].period_end == date(2026, 3, 31)
    assert table.yearly[-1].period_end == date(2022, 3, 31)


def test_margins_match_synthetic_fixture() -> None:
    snap = _snapshot(years=5)
    table = compute_ratios(snap)
    fy26 = table.yearly[0]
    # gross 30%, operating 15%, net = 10000/100000 = 10%.
    assert fy26.gross_margin_pct == pytest.approx(30.0)
    assert fy26.operating_margin_pct == pytest.approx(15.0)
    assert fy26.net_margin_pct == pytest.approx(10.0)


def test_roe_and_debt_to_equity() -> None:
    snap = _snapshot(years=5)
    table = compute_ratios(snap)
    fy26 = table.yearly[0]
    # ROE = NI / equity = 10000 / 50000 = 20%
    assert fy26.roe_pct == pytest.approx(20.0)
    # D/E = 0.45
    assert fy26.debt_to_equity == pytest.approx(0.45)


def test_growth_rates_3y_cagr() -> None:
    snap = _snapshot(years=5)
    table = compute_ratios(snap)
    # Revenue grows at exactly 10% per year in the fixture.
    assert table.growth.revenue_cagr_3y_pct == pytest.approx(10.0, abs=0.01)
    # NI grows at exactly 12% per year.
    assert table.growth.net_income_cagr_3y_pct == pytest.approx(12.0, abs=0.01)


def test_ratios_are_none_when_inputs_missing() -> None:
    snap = FinancialsSnapshot(
        ticker="GAPCO",
        yfinance_symbol="GAPCO.NS",
        exchange="NSE",
        income_statement=[
            IncomeStatementYear(period_end=date(2026, 3, 31)),  # all fields None
        ],
        balance_sheet=[
            BalanceSheetYear(period_end=date(2026, 3, 31)),
        ],
        cash_flow=[
            CashFlowYear(period_end=date(2026, 3, 31)),
        ],
        fetched_at=datetime.now(UTC),
    )
    table = compute_ratios(snap)
    assert len(table.yearly) == 1
    fy = table.yearly[0]
    assert fy.gross_margin_pct is None
    assert fy.roe_pct is None
    assert fy.debt_to_equity is None


def test_zero_division_is_safe() -> None:
    """If equity is zero, ROE should be None — never inf or NaN."""
    snap = FinancialsSnapshot(
        ticker="ZEROEQ",
        yfinance_symbol="ZEROEQ.NS",
        exchange="NSE",
        income_statement=[
            IncomeStatementYear(period_end=date(2026, 3, 31), net_income=1_000.0),
        ],
        balance_sheet=[
            BalanceSheetYear(period_end=date(2026, 3, 31), total_equity=0.0),
        ],
        cash_flow=[
            CashFlowYear(period_end=date(2026, 3, 31)),
        ],
        fetched_at=datetime.now(UTC),
    )
    table = compute_ratios(snap)
    assert table.yearly[0].roe_pct is None
