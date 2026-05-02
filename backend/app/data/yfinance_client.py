"""Async wrapper around the synchronous yfinance library.

yfinance is synchronous and does its own HTTP under the hood; we run blocking
calls in `asyncio.to_thread` so FastAPI's event loop stays responsive.

Row-label lookups are intentionally defensive: yfinance occasionally renames
or splits rows between releases, so we try a small ordered list of candidate
labels for each financial line item. If none match, the field is left None
and downstream code treats it as missing data (rather than crashing).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
import yfinance as yf
from pandas import DataFrame, isna

from app.core.config import Settings
from app.schemas.financials import (
    BalanceSheetYear,
    CashFlowYear,
    Exchange,
    FinancialsSnapshot,
    IncomeStatementYear,
    QuoteSnapshot,
)
from app.schemas.valuation import (
    HistoricalValuationPoint,
    ValuationMultiples,
)
from app.services.cache import CacheService

log = structlog.get_logger(__name__)

_INCOME_ROWS: dict[str, tuple[str, ...]] = {
    "revenue": ("Total Revenue", "Operating Revenue"),
    "gross_profit": ("Gross Profit",),
    "operating_income": ("Operating Income",),
    "ebit": ("EBIT",),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
    "net_income": ("Net Income", "Net Income Common Stockholders"),
    "interest_expense": ("Interest Expense", "Interest Expense Non Operating"),
    "basic_eps": ("Basic EPS",),
    "diluted_eps": ("Diluted EPS",),
    "diluted_shares": ("Diluted Average Shares",),
}

_BALANCE_ROWS: dict[str, tuple[str, ...]] = {
    "total_assets": ("Total Assets",),
    "current_assets": ("Current Assets",),
    "total_liabilities": (
        "Total Liabilities Net Minority Interest",
        "Total Liabilities",
    ),
    "non_current_liabilities": ("Total Non Current Liabilities Net Minority Interest",),
    "total_equity": (
        "Stockholders Equity",
        "Common Stock Equity",
        "Total Equity Gross Minority Interest",
    ),
    "total_debt": ("Total Debt",),
    "cash_and_equivalents": (
        "Cash And Cash Equivalents",
        "Cash Cash Equivalents And Short Term Investments",
    ),
    "working_capital": ("Working Capital",),
    "invested_capital": ("Invested Capital",),
}

_CASHFLOW_ROWS: dict[str, tuple[str, ...]] = {
    "operating_cash_flow": ("Operating Cash Flow",),
    "capex": ("Capital Expenditure", "Capital Expenditure Reported"),
    "free_cash_flow": ("Free Cash Flow",),
    "dividends_paid": ("Cash Dividends Paid",),
}


def resolve_symbol(ticker: str) -> tuple[str, Exchange]:
    """Map user input (e.g. ``RELIANCE``) to a yfinance symbol + exchange.

    Defaults to NSE because nearly every ticker we care about lists there.
    Explicit ``.NS`` / ``.BO`` suffixes are honoured.
    """
    upper = ticker.strip().upper()
    if upper.endswith(".NS"):
        return upper, "NSE"
    if upper.endswith(".BO"):
        return upper, "BSE"
    return f"{upper}.NS", "NSE"


def _safe_float(value: Any) -> float | None:
    """Coerce an arbitrary cell value (numpy float, NaN, str, None) to float|None."""
    if value is None:
        return None
    try:
        if isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_value(df: DataFrame, candidates: tuple[str, ...], col: Any) -> float | None:
    for label in candidates:
        if label in df.index:
            return _safe_float(df.loc[label, col])
    return None


def _columns_descending(df: DataFrame) -> list[Any]:
    """yfinance generally returns newest-first; sort defensively."""
    return sorted(list(df.columns), reverse=True)


def _close_on_or_before(close_by_date: dict[Any, float], target: Any) -> float | None:
    """Return the closing price on the most recent trading date ≤ `target`.

    Used to map a fiscal year-end (e.g. 2024-03-31) onto the nearest
    previous monthly close in our 1-month-interval history.
    """
    candidates = [d for d in close_by_date if d <= target]
    if not candidates:
        return None
    return close_by_date[max(candidates)]


def _to_date(col: Any) -> Any:
    if hasattr(col, "date"):
        return col.date()
    return col


class YFinanceClient:
    """Async wrapper around yfinance with pluggable Pydantic-typed cache."""

    def __init__(self, cache: CacheService, settings: Settings) -> None:
        self._cache = cache
        self._settings = settings

    async def fetch_quote(self, ticker: str) -> QuoteSnapshot:
        symbol, exchange = resolve_symbol(ticker)
        cache_key = f"yfinance:quote:{symbol}"

        cached = await self._cache.get(cache_key, QuoteSnapshot)
        if cached is not None:
            return cached

        log.info("yfinance.fetch_quote.start", ticker=ticker, symbol=symbol)
        snapshot = await asyncio.to_thread(self._blocking_quote, ticker, symbol, exchange)

        # Quotes are time-sensitive: cap TTL at 5 min regardless of config.
        ttl = min(300, self._settings.CACHE_TTL_YFINANCE_SECONDS)
        await self._cache.set(cache_key, snapshot, ttl_seconds=ttl)
        log.info(
            "yfinance.fetch_quote.done",
            ticker=ticker,
            price=snapshot.current_price,
            currency=snapshot.currency,
        )
        return snapshot

    async def fetch_current_multiples(self, ticker: str) -> ValuationMultiples:
        symbol, _ = resolve_symbol(ticker)
        cache_key = f"yfinance:multiples:{symbol}"
        cached = await self._cache.get(cache_key, ValuationMultiples)
        if cached is not None:
            return cached

        log.info("yfinance.fetch_current_multiples.start", ticker=ticker, symbol=symbol)
        multiples = await asyncio.to_thread(self._blocking_current_multiples, symbol)
        # Multiples are mid-term sticky — cache 1 hour, capped by config.
        ttl = min(3600, self._settings.CACHE_TTL_YFINANCE_SECONDS)
        await self._cache.set(cache_key, multiples, ttl_seconds=ttl)
        return multiples

    async def fetch_historical_valuation_points(
        self, ticker: str, num_years: int = 6
    ) -> list[HistoricalValuationPoint]:
        """Per-fiscal-year P/E and P/B for the available history.

        Combines (a) the financials snapshot already produced by
        `fetch_financials` with (b) monthly close prices around each fiscal
        year-end. Indian fiscal year ends 31 March; we pick the last
        available monthly close on or before the FY end date.
        """
        symbol, _ = resolve_symbol(ticker)
        cache_key = f"yfinance:histval:{symbol}:{num_years}"
        cached_raw = await self._cache._redis.get(cache_key)  # noqa: SLF001
        if cached_raw is not None:
            from pydantic import TypeAdapter

            return TypeAdapter(list[HistoricalValuationPoint]).validate_json(cached_raw)

        log.info(
            "yfinance.fetch_historical_valuation.start",
            ticker=ticker,
            symbol=symbol,
            years=num_years,
        )
        snapshot = await self.fetch_financials(ticker)
        points = await asyncio.to_thread(
            self._blocking_historical_valuation, symbol, snapshot, num_years
        )

        from pydantic import TypeAdapter

        adapter = TypeAdapter(list[HistoricalValuationPoint])
        await self._cache._redis.set(  # noqa: SLF001
            cache_key,
            adapter.dump_json(points),
            ex=self._settings.CACHE_TTL_YFINANCE_SECONDS,
        )
        return points

    async def fetch_financials(self, ticker: str) -> FinancialsSnapshot:
        symbol, exchange = resolve_symbol(ticker)
        cache_key = f"yfinance:financials:{symbol}"

        cached = await self._cache.get(cache_key, FinancialsSnapshot)
        if cached is not None:
            return cached

        log.info("yfinance.fetch_financials.start", ticker=ticker, symbol=symbol)
        snapshot = await asyncio.to_thread(
            self._blocking_financials, ticker, symbol, exchange
        )
        await self._cache.set(
            cache_key, snapshot, ttl_seconds=self._settings.CACHE_TTL_YFINANCE_SECONDS
        )
        log.info(
            "yfinance.fetch_financials.done",
            ticker=ticker,
            years_income=len(snapshot.income_statement),
            years_balance=len(snapshot.balance_sheet),
            years_cashflow=len(snapshot.cash_flow),
        )
        return snapshot

    @staticmethod
    def _blocking_current_multiples(symbol: str) -> ValuationMultiples:
        from datetime import UTC, datetime as _dt

        t = yf.Ticker(symbol)
        info = t.info or {}

        # yfinance's `dividendYield` is unreliable across versions: sometimes
        # decimal (0.0038), sometimes percent (0.38). Compute it ourselves
        # from dividendRate / currentPrice when both are present, then fall
        # back to whatever info had.
        dy_pct: float | None = None
        rate = _safe_float(info.get("dividendRate"))
        price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        if rate is not None and price is not None and price > 0:
            dy_pct = rate / price * 100.0
        else:
            raw_dy = _safe_float(info.get("dividendYield"))
            if raw_dy is not None:
                # Heuristic: if value looks like a decimal fraction, convert.
                dy_pct = raw_dy * 100.0 if abs(raw_dy) < 1.0 else raw_dy

        payout_raw = _safe_float(info.get("payoutRatio"))
        payout_pct = payout_raw * 100.0 if payout_raw is not None else None

        return ValuationMultiples(
            current_price=price,
            market_cap=_safe_float(info.get("marketCap")),
            enterprise_value=_safe_float(info.get("enterpriseValue")),
            trailing_pe=_safe_float(info.get("trailingPE")),
            forward_pe=_safe_float(info.get("forwardPE")),
            price_to_book=_safe_float(info.get("priceToBook")),
            price_to_sales_ttm=_safe_float(info.get("priceToSalesTrailing12Months")),
            ev_to_ebitda=_safe_float(info.get("enterpriseToEbitda")),
            ev_to_revenue=_safe_float(info.get("enterpriseToRevenue")),
            dividend_yield_pct=dy_pct,
            payout_ratio_pct=payout_pct,
            book_value_per_share=_safe_float(info.get("bookValue")),
            trailing_eps=_safe_float(info.get("trailingEps")),
            forward_eps=_safe_float(info.get("forwardEps")),
            fifty_two_week_high=_safe_float(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_safe_float(info.get("fiftyTwoWeekLow")),
            fetched_at=_dt.now(UTC),
        )

    @staticmethod
    def _blocking_historical_valuation(
        symbol: str, snapshot: FinancialsSnapshot, num_years: int
    ) -> list[HistoricalValuationPoint]:
        """Pick a close price near each fiscal year-end and combine with EPS / book value."""
        from datetime import datetime as _dt
        from datetime import timedelta

        t = yf.Ticker(symbol)
        # Monthly history covers all FY-ends we care about. Pull a year of
        # buffer on either side so the "closest before FY end" lookup never
        # falls off the start of the series.
        try:
            hist = t.history(period=f"{num_years + 1}y", interval="1mo")
        except Exception:
            hist = None

        # Build a simple {date: close} map. Strip the timezone so date math
        # against `period_end` (naive date) is straightforward.
        close_by_date: dict[date, float] = {}
        if hist is not None and not hist.empty:
            for ts, row in hist["Close"].items():
                d = ts.date() if hasattr(ts, "date") else None
                close_value = _safe_float(row)
                if d is not None and close_value is not None:
                    close_by_date[d] = close_value

        # Build per-year IS / BS lookups for EPS + book value.
        is_by_year = {y.period_end: y for y in snapshot.income_statement}
        bs_by_year = {y.period_end: y for y in snapshot.balance_sheet}

        # Use the IS years as the canonical list — that is what defines a
        # "fiscal year of data". Newest first.
        fy_ends = sorted(is_by_year.keys(), reverse=True)

        points: list[HistoricalValuationPoint] = []
        for fy_end in fy_ends:
            close_price = _close_on_or_before(close_by_date, fy_end)
            inc = is_by_year.get(fy_end)
            bal = bs_by_year.get(fy_end)

            # Diluted EPS first; fall back to basic.
            eps = (inc.diluted_eps if inc else None) or (inc.basic_eps if inc else None)

            # Book value per share. Prefer total_equity / diluted_shares
            # since they come from the same accounting snapshot. Otherwise
            # fall back to (a) total_equity / sharesOutstanding from info,
            # which we don't have here, so leave None.
            bvps: float | None = None
            if bal and inc and bal.total_equity and inc.diluted_shares:
                bvps = bal.total_equity / inc.diluted_shares

            pe = close_price / eps if (close_price and eps and eps > 0) else None
            pb = close_price / bvps if (close_price and bvps and bvps > 0) else None

            points.append(
                HistoricalValuationPoint(
                    period_end=fy_end,
                    fy_end_close_price=close_price,
                    eps_for_year=eps,
                    book_value_per_share=bvps,
                    pe=pe,
                    pb=pb,
                )
            )
        return points

    @staticmethod
    def _blocking_quote(ticker: str, symbol: str, exchange: Exchange) -> QuoteSnapshot:
        t = yf.Ticker(symbol)
        info = t.info or {}
        return QuoteSnapshot(
            ticker=ticker,
            yfinance_symbol=symbol,
            exchange=exchange,
            company_name=info.get("longName") or info.get("shortName"),
            current_price=_safe_float(
                info.get("currentPrice") or info.get("regularMarketPrice")
            ),
            market_cap=_safe_float(info.get("marketCap")),
            shares_outstanding=_safe_float(info.get("sharesOutstanding")),
            currency=info.get("currency", "INR"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            fetched_at=datetime.now(UTC),
        )

    @staticmethod
    def _blocking_financials(
        ticker: str, symbol: str, exchange: Exchange
    ) -> FinancialsSnapshot:
        t = yf.Ticker(symbol)
        info = t.info or {}
        income_df = t.income_stmt
        balance_df = t.balance_sheet
        cashflow_df = t.cashflow

        income_years = _parse_income(income_df)
        balance_years = _parse_balance(balance_df)
        cashflow_years = _parse_cashflow(cashflow_df)

        return FinancialsSnapshot(
            ticker=ticker,
            yfinance_symbol=symbol,
            exchange=exchange,
            company_name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            currency=info.get("currency", "INR"),
            income_statement=income_years,
            balance_sheet=balance_years,
            cash_flow=cashflow_years,
            fetched_at=datetime.now(UTC),
        )


def _parse_income(df: DataFrame | None) -> list[IncomeStatementYear]:
    if df is None or df.empty:
        return []
    out: list[IncomeStatementYear] = []
    for col in _columns_descending(df):
        out.append(
            IncomeStatementYear(
                period_end=_to_date(col),
                revenue=_row_value(df, _INCOME_ROWS["revenue"], col),
                gross_profit=_row_value(df, _INCOME_ROWS["gross_profit"], col),
                operating_income=_row_value(df, _INCOME_ROWS["operating_income"], col),
                ebit=_row_value(df, _INCOME_ROWS["ebit"], col),
                ebitda=_row_value(df, _INCOME_ROWS["ebitda"], col),
                net_income=_row_value(df, _INCOME_ROWS["net_income"], col),
                interest_expense=_row_value(df, _INCOME_ROWS["interest_expense"], col),
                basic_eps=_row_value(df, _INCOME_ROWS["basic_eps"], col),
                diluted_eps=_row_value(df, _INCOME_ROWS["diluted_eps"], col),
                diluted_shares=_row_value(df, _INCOME_ROWS["diluted_shares"], col),
            )
        )
    return out


def _parse_balance(df: DataFrame | None) -> list[BalanceSheetYear]:
    if df is None or df.empty:
        return []
    out: list[BalanceSheetYear] = []
    for col in _columns_descending(df):
        total_liab = _row_value(df, _BALANCE_ROWS["total_liabilities"], col)
        non_curr_liab = _row_value(df, _BALANCE_ROWS["non_current_liabilities"], col)
        current_liab: float | None = None
        if total_liab is not None and non_curr_liab is not None:
            current_liab = total_liab - non_curr_liab
        out.append(
            BalanceSheetYear(
                period_end=_to_date(col),
                total_assets=_row_value(df, _BALANCE_ROWS["total_assets"], col),
                current_assets=_row_value(df, _BALANCE_ROWS["current_assets"], col),
                total_liabilities=total_liab,
                non_current_liabilities=non_curr_liab,
                current_liabilities=current_liab,
                total_equity=_row_value(df, _BALANCE_ROWS["total_equity"], col),
                total_debt=_row_value(df, _BALANCE_ROWS["total_debt"], col),
                cash_and_equivalents=_row_value(
                    df, _BALANCE_ROWS["cash_and_equivalents"], col
                ),
                working_capital=_row_value(df, _BALANCE_ROWS["working_capital"], col),
                invested_capital=_row_value(df, _BALANCE_ROWS["invested_capital"], col),
            )
        )
    return out


def _parse_cashflow(df: DataFrame | None) -> list[CashFlowYear]:
    if df is None or df.empty:
        return []
    out: list[CashFlowYear] = []
    for col in _columns_descending(df):
        out.append(
            CashFlowYear(
                period_end=_to_date(col),
                operating_cash_flow=_row_value(
                    df, _CASHFLOW_ROWS["operating_cash_flow"], col
                ),
                capex=_row_value(df, _CASHFLOW_ROWS["capex"], col),
                free_cash_flow=_row_value(df, _CASHFLOW_ROWS["free_cash_flow"], col),
                dividends_paid=_row_value(df, _CASHFLOW_ROWS["dividends_paid"], col),
            )
        )
    return out
