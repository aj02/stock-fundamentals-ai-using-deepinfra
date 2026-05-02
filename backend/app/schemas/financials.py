"""Pydantic models for the data layer.

Floats (not Decimal) are intentional. yfinance returns numpy floats; the
showcase trades a tiny amount of precision for end-to-end simplicity. If
this code ever ran in a context that affected money, switch to Decimal.

All models are `frozen=True` — once a snapshot is fetched, it shouldn't
mutate. Cache layer reads/writes them as JSON via Pydantic.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Exchange = Literal["NSE", "BSE", "UNKNOWN"]


class IncomeStatementYear(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_end: date
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    ebit: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    interest_expense: float | None = None
    basic_eps: float | None = None
    diluted_eps: float | None = None
    diluted_shares: float | None = None


class BalanceSheetYear(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_end: date
    total_assets: float | None = None
    current_assets: float | None = None
    total_liabilities: float | None = None
    non_current_liabilities: float | None = None
    # `current_liabilities` is derived: total - non-current. yfinance does not
    # expose it directly for Indian equities.
    current_liabilities: float | None = None
    total_equity: float | None = None
    total_debt: float | None = None
    cash_and_equivalents: float | None = None
    working_capital: float | None = None
    invested_capital: float | None = None


class CashFlowYear(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_end: date
    operating_cash_flow: float | None = None
    capex: float | None = None
    free_cash_flow: float | None = None
    dividends_paid: float | None = None


class FinancialsSnapshot(BaseModel):
    """Multi-year financials snapshot for one ticker, as returned by yfinance."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    yfinance_symbol: str
    exchange: Exchange
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str = "INR"
    income_statement: list[IncomeStatementYear] = Field(default_factory=list)
    balance_sheet: list[BalanceSheetYear] = Field(default_factory=list)
    cash_flow: list[CashFlowYear] = Field(default_factory=list)
    fetched_at: datetime
    source: Literal["yfinance"] = "yfinance"


class QuoteSnapshot(BaseModel):
    """Lightweight current-price snapshot — refreshed more aggressively than financials."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    yfinance_symbol: str
    exchange: Exchange
    company_name: str | None = None
    current_price: float | None = None
    market_cap: float | None = None
    shares_outstanding: float | None = None
    currency: str = "INR"
    sector: str | None = None
    industry: str | None = None
    fetched_at: datetime
    source: Literal["yfinance"] = "yfinance"


class ScreenerAnnualReportLink(BaseModel):
    """One annual-report PDF link as listed on a Screener company page."""

    model_config = ConfigDict(frozen=True)

    fiscal_year_label: str  # As shown on Screener, e.g. "Financial Year 2025from bse"
    fiscal_year: int | None = None  # Parsed integer year (e.g. 2025) when extractable
    source: Literal["bse", "nse", "company", "unknown"] = "unknown"
    url: str


class ScreenerSnapshot(BaseModel):
    """Screener.in-derived snapshot of a company page.

    STEP 6 STATUS: real implementation. Parses the company / consolidated
    page for: company name, Pros/Cons bullets, and Annual Report links.
    Peer comparison ships via a separate AJAX endpoint and is left for a
    later cleanup pass (the Valuation Agent already degrades gracefully).
    """

    model_config = ConfigDict(frozen=True)

    ticker: str
    available: bool = False
    company_name: str | None = None
    pros: list[str] = []
    cons: list[str] = []
    annual_reports: list[ScreenerAnnualReportLink] = []
    source_url: str | None = None
    note: str | None = None
    fetched_at: datetime
