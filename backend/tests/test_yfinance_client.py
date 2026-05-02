"""Unit tests for the yfinance parser.

Network calls are mocked — we feed synthetic DataFrames in the shape yfinance
actually returns (rows-as-line-items, columns-as-period-ends) and assert the
parser maps them onto the Pydantic snapshot correctly. Live shape was
captured against RELIANCE.NS during step 3 development.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.core.config import Settings
from app.data.yfinance_client import YFinanceClient, resolve_symbol


def _income_df() -> pd.DataFrame:
    cols = [pd.Timestamp("2026-03-31"), pd.Timestamp("2025-03-31")]
    return pd.DataFrame(
        {
            cols[0]: {
                "Total Revenue": 10_572_190_000_000.0,
                "Gross Profit": 3_500_000_000_000.0,
                "Operating Income": 1_200_000_000_000.0,
                "EBIT": 1_220_000_000_000.0,
                "EBITDA": 1_900_000_000_000.0,
                "Net Income": 807_750_000_000.0,
                "Interest Expense": 250_000_000_000.0,
                "Basic EPS": 60.0,
                "Diluted EPS": 59.5,
                "Diluted Average Shares": 13_532_472_635.0,
            },
            cols[1]: {
                "Total Revenue": 9_646_930_000_000.0,
                "Net Income": 696_480_000_000.0,
            },
        }
    )


def _balance_df() -> pd.DataFrame:
    cols = [pd.Timestamp("2026-03-31"), pd.Timestamp("2025-03-31")]
    return pd.DataFrame(
        {
            cols[0]: {
                "Total Assets": 17_000_000_000_000.0,
                "Current Assets": 4_000_000_000_000.0,
                "Total Liabilities Net Minority Interest": 8_500_000_000_000.0,
                "Total Non Current Liabilities Net Minority Interest": 5_000_000_000_000.0,
                "Stockholders Equity": 8_000_000_000_000.0,
                "Total Debt": 3_500_000_000_000.0,
                "Cash And Cash Equivalents": 800_000_000_000.0,
                "Working Capital": 500_000_000_000.0,
                "Invested Capital": 11_000_000_000_000.0,
            },
            cols[1]: {
                "Total Assets": 16_000_000_000_000.0,
                "Stockholders Equity": 7_500_000_000_000.0,
            },
        }
    )


def _cashflow_df() -> pd.DataFrame:
    cols = [pd.Timestamp("2026-03-31"), pd.Timestamp("2025-03-31")]
    return pd.DataFrame(
        {
            cols[0]: {
                "Operating Cash Flow": 1_500_000_000_000.0,
                "Capital Expenditure": -800_000_000_000.0,
                "Free Cash Flow": 700_000_000_000.0,
                "Cash Dividends Paid": -50_000_000_000.0,
            },
            cols[1]: {
                "Operating Cash Flow": 1_400_000_000_000.0,
            },
        }
    )


def _make_ticker_mock() -> MagicMock:
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "longName": "Reliance Industries Limited",
        "sector": "Energy",
        "industry": "Oil & Gas Refining & Marketing",
        "currency": "INR",
        "currentPrice": 1436.0,
        "marketCap": 19_432_629_862_400,
        "sharesOutstanding": 13_532_472_634,
    }
    mock_ticker.income_stmt = _income_df()
    mock_ticker.balance_sheet = _balance_df()
    mock_ticker.cashflow = _cashflow_df()
    return mock_ticker


@pytest.mark.parametrize(
    ("user_input", "expected_symbol", "expected_exchange"),
    [
        ("RELIANCE", "RELIANCE.NS", "NSE"),
        ("reliance", "RELIANCE.NS", "NSE"),
        ("INFY.NS", "INFY.NS", "NSE"),
        ("HDFCBANK.BO", "HDFCBANK.BO", "BSE"),
    ],
)
def test_resolve_symbol(user_input: str, expected_symbol: str, expected_exchange: str) -> None:
    symbol, exchange = resolve_symbol(user_input)
    assert symbol == expected_symbol
    assert exchange == expected_exchange


async def test_fetch_financials_parses_income_balance_cashflow() -> None:
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()

    settings = Settings()
    client = YFinanceClient(cache=cache, settings=settings)

    with patch("app.data.yfinance_client.yf.Ticker", return_value=_make_ticker_mock()):
        snapshot = await client.fetch_financials("RELIANCE")

    assert snapshot.ticker == "RELIANCE"
    assert snapshot.yfinance_symbol == "RELIANCE.NS"
    assert snapshot.exchange == "NSE"
    assert snapshot.company_name == "Reliance Industries Limited"
    assert snapshot.currency == "INR"

    # Two years populated, newest first.
    assert len(snapshot.income_statement) == 2
    fy26 = snapshot.income_statement[0]
    assert fy26.period_end == date(2026, 3, 31)
    assert fy26.revenue == 10_572_190_000_000.0
    assert fy26.net_income == 807_750_000_000.0
    assert fy26.diluted_eps == 59.5

    fy25 = snapshot.income_statement[1]
    assert fy25.period_end == date(2025, 3, 31)
    # Missing rows in fixture come through as None, not crash.
    assert fy25.gross_profit is None
    assert fy25.revenue == 9_646_930_000_000.0

    # Balance sheet with derived current_liabilities.
    bs26 = snapshot.balance_sheet[0]
    assert bs26.total_liabilities == 8_500_000_000_000.0
    assert bs26.non_current_liabilities == 5_000_000_000_000.0
    assert bs26.current_liabilities == 3_500_000_000_000.0  # 8.5T − 5T

    cf26 = snapshot.cash_flow[0]
    assert cf26.operating_cash_flow == 1_500_000_000_000.0
    assert cf26.free_cash_flow == 700_000_000_000.0

    # Cache write happened with the correct TTL.
    cache.set.assert_awaited_once()
    args, kwargs = cache.set.call_args
    assert args[0] == "yfinance:financials:RELIANCE.NS"
    assert kwargs["ttl_seconds"] == settings.CACHE_TTL_YFINANCE_SECONDS


async def test_fetch_financials_returns_cached_when_available() -> None:
    """Verify cache short-circuits the network call entirely."""
    settings = Settings()
    cache = MagicMock()

    # Build a "previously cached" snapshot we'll pretend to read back.
    with patch("app.data.yfinance_client.yf.Ticker", return_value=_make_ticker_mock()):
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        first = await YFinanceClient(cache, settings).fetch_financials("RELIANCE")

    cache.get = AsyncMock(return_value=first)
    cache.set = AsyncMock()
    with patch("app.data.yfinance_client.yf.Ticker", side_effect=AssertionError("must not be called")) as mock_yf:
        second = await YFinanceClient(cache, settings).fetch_financials("RELIANCE")
        mock_yf.assert_not_called()

    assert second == first
    cache.set.assert_not_awaited()


async def test_fetch_financials_handles_empty_dataframes() -> None:
    """If yfinance returns nothing, snapshot is still well-formed (lists empty)."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()

    empty_ticker = MagicMock()
    empty_ticker.info = {"currency": "INR"}
    empty_ticker.income_stmt = pd.DataFrame()
    empty_ticker.balance_sheet = pd.DataFrame()
    empty_ticker.cashflow = pd.DataFrame()

    with patch("app.data.yfinance_client.yf.Ticker", return_value=empty_ticker):
        snapshot = await YFinanceClient(cache, Settings()).fetch_financials("EMPTYCO")

    assert snapshot.income_statement == []
    assert snapshot.balance_sheet == []
    assert snapshot.cash_flow == []
    assert snapshot.currency == "INR"
