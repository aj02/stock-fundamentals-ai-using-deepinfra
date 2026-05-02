"""End-to-end smoke test for the data layer.

Fetches RELIANCE.NS financials + quote via YFinanceClient, exercises the
Pydantic-typed Redis cache (cold miss → live fetch → warm hit), and prints
a concise human-readable summary so we can eyeball the shape.

Usage (from inside a container with REDIS_URL pointing at the compose redis):
    python -m scripts.smoke_yfinance RELIANCE
"""

from __future__ import annotations

import asyncio
import sys

import structlog

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.data.yfinance_client import YFinanceClient
from app.services.cache import CacheService

log = structlog.get_logger("smoke")


def _fmt_inr(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 1e7:  # ≥ 1 crore
        return f"₹{value / 1e7:,.1f} cr"
    return f"₹{value:,.0f}"


async def main(ticker: str) -> int:
    configure_logging("INFO")
    settings = get_settings()
    cache = CacheService.from_url(settings.REDIS_URL)
    client = YFinanceClient(cache=cache, settings=settings)

    cache_key_fin = f"yfinance:financials:{ticker.upper()}.NS"
    cache_key_q = f"yfinance:quote:{ticker.upper()}.NS"
    await cache.delete(cache_key_fin)
    await cache.delete(cache_key_q)

    print(f"\n=== {ticker} — cold fetch ===")
    quote = await client.fetch_quote(ticker)
    fin = await client.fetch_financials(ticker)

    print(f"\n  {fin.company_name}  ({fin.exchange})  [{fin.currency}]")
    print(f"  Sector: {fin.sector}  /  Industry: {fin.industry}")
    print(f"  Last price: {_fmt_inr(quote.current_price)}    Mkt cap: {_fmt_inr(quote.market_cap)}")
    print(f"  yfinance symbol: {fin.yfinance_symbol}")
    print(f"  Years available — IS: {len(fin.income_statement)}, BS: {len(fin.balance_sheet)}, CF: {len(fin.cash_flow)}")

    print("\n  --- Income statement (newest first) ---")
    print(f"  {'Period':<12}  {'Revenue':>14}  {'Op Income':>14}  {'Net Income':>14}  {'Dil EPS':>9}")
    for row in fin.income_statement:
        print(
            f"  {row.period_end!s:<12}  {_fmt_inr(row.revenue):>14}  "
            f"{_fmt_inr(row.operating_income):>14}  {_fmt_inr(row.net_income):>14}  "
            f"{(f'{row.diluted_eps:.2f}' if row.diluted_eps is not None else '—'):>9}"
        )

    print("\n  --- Balance sheet (newest first) ---")
    print(f"  {'Period':<12}  {'Tot Assets':>14}  {'Tot Equity':>14}  {'Tot Debt':>14}  {'Curr Liab':>14}")
    for row in fin.balance_sheet:
        print(
            f"  {row.period_end!s:<12}  {_fmt_inr(row.total_assets):>14}  "
            f"{_fmt_inr(row.total_equity):>14}  {_fmt_inr(row.total_debt):>14}  "
            f"{_fmt_inr(row.current_liabilities):>14}"
        )

    print("\n  --- Cash flow (newest first) ---")
    print(f"  {'Period':<12}  {'Op CF':>14}  {'Capex':>14}  {'Free CF':>14}  {'Dividends':>14}")
    for row in fin.cash_flow:
        print(
            f"  {row.period_end!s:<12}  {_fmt_inr(row.operating_cash_flow):>14}  "
            f"{_fmt_inr(row.capex):>14}  {_fmt_inr(row.free_cash_flow):>14}  "
            f"{_fmt_inr(row.dividends_paid):>14}"
        )

    # Cache roundtrip — second fetch should hit Redis without touching yfinance.
    print(f"\n=== {ticker} — warm fetch (should hit Redis cache) ===")
    fin2 = await client.fetch_financials(ticker)
    same = (
        fin2.fetched_at == fin.fetched_at
        and fin2.income_statement == fin.income_statement
    )
    print(f"  cache hit: {same}  (fetched_at unchanged: {fin2.fetched_at == fin.fetched_at})")

    await cache.aclose()
    return 0 if same else 1


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    raise SystemExit(asyncio.run(main(arg)))
