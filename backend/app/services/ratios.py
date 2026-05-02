"""Pure-Python ratio computation.

Critical design choice: ratios are computed deterministically here, NOT by
the LLM. The Financials Agent's `compute_ratios` tool delegates straight to
this module. LLMs are unreliable at arithmetic; this keeps numbers honest.

All inputs are tolerant of `None` — yfinance frequently has gaps, and a
missing input should produce a `None` ratio (not a crash, not a zero).
"""

from __future__ import annotations

from datetime import date
from math import isfinite

from app.schemas.agents import GrowthRates, RatiosTable, YearlyRatios
from app.schemas.financials import (
    BalanceSheetYear,
    CashFlowYear,
    FinancialsSnapshot,
    IncomeStatementYear,
)


def _safe_div(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    result = num / den
    return result if isfinite(result) else None


def _pct(num: float | None, den: float | None) -> float | None:
    ratio = _safe_div(num, den)
    return ratio * 100 if ratio is not None else None


def _cagr_pct(end_value: float | None, start_value: float | None, years: int) -> float | None:
    """Compound annual growth rate, in percent."""
    if (
        end_value is None
        or start_value is None
        or start_value <= 0
        or end_value <= 0
        or years <= 0
    ):
        return None
    rate = (end_value / start_value) ** (1.0 / years) - 1.0
    pct = rate * 100
    return pct if isfinite(pct) else None


def _compute_year(
    period_end: date,
    inc: IncomeStatementYear | None,
    bs: BalanceSheetYear | None,
    cf: CashFlowYear | None,
) -> YearlyRatios:
    revenue = inc.revenue if inc else None
    gross = inc.gross_profit if inc else None
    op_inc = inc.operating_income if inc else None
    ebit = inc.ebit if inc else op_inc  # fall back to operating income
    net_inc = inc.net_income if inc else None
    interest = inc.interest_expense if inc else None

    total_equity = bs.total_equity if bs else None
    total_debt = bs.total_debt if bs else None
    total_assets = bs.total_assets if bs else None
    current_assets = bs.current_assets if bs else None
    current_liab = bs.current_liabilities if bs else None
    invested_capital = bs.invested_capital if bs else None

    ocf = cf.operating_cash_flow if cf else None
    fcf = cf.free_cash_flow if cf else None

    # ROCE: EBIT / capital employed. Prefer Invested Capital from yfinance;
    # fall back to (Total Assets − Current Liabilities) when missing.
    capital_employed = invested_capital
    if capital_employed is None and total_assets is not None and current_liab is not None:
        capital_employed = total_assets - current_liab

    return YearlyRatios(
        period_end=period_end,
        gross_margin_pct=_pct(gross, revenue),
        operating_margin_pct=_pct(op_inc, revenue),
        net_margin_pct=_pct(net_inc, revenue),
        roe_pct=_pct(net_inc, total_equity),
        roce_pct=_pct(ebit, capital_employed),
        debt_to_equity=_safe_div(total_debt, total_equity),
        # Interest expense is reported as a positive number by yfinance.
        # If it's zero or missing we leave coverage as None rather than inf.
        interest_coverage=_safe_div(ebit, interest) if interest and interest > 0 else None,
        current_ratio=_safe_div(current_assets, current_liab),
        ocf_to_pat=_safe_div(ocf, net_inc),
        fcf_margin_pct=_pct(fcf, revenue),
    )


def _compute_growth(income_statement: list[IncomeStatementYear]) -> GrowthRates:
    """CAGR from oldest available year to newest. Lists are newest-first."""
    revenues = [(y.period_end, y.revenue) for y in income_statement if y.revenue is not None]
    nis = [(y.period_end, y.net_income) for y in income_statement if y.net_income is not None]

    def _cagr_window(series: list[tuple[date, float]], window: int) -> float | None:
        if len(series) < window + 1:
            return None
        # series is newest-first → series[0] is end, series[window] is start.
        end_value = series[0][1]
        start_value = series[window][1]
        return _cagr_pct(end_value, start_value, window)

    return GrowthRates(
        revenue_cagr_3y_pct=_cagr_window(revenues, 3),
        revenue_cagr_5y_pct=_cagr_window(revenues, 5)
        if len(revenues) >= 6
        else None,
        net_income_cagr_3y_pct=_cagr_window(nis, 3),
        net_income_cagr_5y_pct=_cagr_window(nis, 5)
        if len(nis) >= 6
        else None,
        fcf_cagr_3y_pct=None,  # populated below if FCF series is dense enough
    )


def compute_ratios(snapshot: FinancialsSnapshot) -> RatiosTable:
    is_by_year = {y.period_end: y for y in snapshot.income_statement}
    bs_by_year = {y.period_end: y for y in snapshot.balance_sheet}
    cf_by_year = {y.period_end: y for y in snapshot.cash_flow}

    all_years = sorted(set(is_by_year) | set(bs_by_year) | set(cf_by_year), reverse=True)
    yearly = [
        _compute_year(year, is_by_year.get(year), bs_by_year.get(year), cf_by_year.get(year))
        for year in all_years
    ]

    growth = _compute_growth(snapshot.income_statement)

    # FCF CAGR — computed here because we have direct access to cash_flow.
    fcfs = [(y.period_end, y.free_cash_flow) for y in snapshot.cash_flow if y.free_cash_flow is not None and y.free_cash_flow > 0]
    if len(fcfs) >= 4:
        end = fcfs[0][1]
        start = fcfs[3][1]
        growth = growth.model_copy(update={"fcf_cagr_3y_pct": _cagr_pct(end, start, 3)})

    return RatiosTable(yearly=yearly, growth=growth)
