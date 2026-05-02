"""Live smoke runner for the Valuation Agent (step 5)."""

from __future__ import annotations

import asyncio
import sys

import structlog

from app.agents.deps import build_agent_deps
from app.agents.valuation import run_valuation_agent
from app.core.logging import configure_logging
from app.schemas.valuation import ValuationReport

log = structlog.get_logger("smoke")


def _fmt(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "—"
    return f"{value:.2f}{suffix}"


def _print_report(r: ValuationReport) -> None:
    cm = r.current_multiples
    h = r.historical_valuation
    m = h.medians

    print(f"\n{'═' * 76}")
    print(f"  {r.company_name}  ({r.yfinance_symbol})")
    print(f"  {r.sector} / {r.industry} · {r.currency}")
    print(f"  Period: {r.period_summary}")
    print(f"{'═' * 76}\n")

    print("  ── Current multiples ──")
    print(f"  Price             {_fmt(cm.current_price)}")
    print(f"  Market cap        {_fmt(cm.market_cap)}")
    print(f"  EV                {_fmt(cm.enterprise_value)}")
    print(f"  Trailing P/E      {_fmt(cm.trailing_pe, '×')}")
    print(f"  Forward P/E       {_fmt(cm.forward_pe, '×')}")
    print(f"  P/B               {_fmt(cm.price_to_book, '×')}")
    print(f"  P/S (TTM)         {_fmt(cm.price_to_sales_ttm, '×')}")
    print(f"  EV/EBITDA         {_fmt(cm.ev_to_ebitda, '×')}")
    print(f"  EV/Revenue        {_fmt(cm.ev_to_revenue, '×')}")
    print(f"  Dividend yield    {_fmt(cm.dividend_yield_pct, '%')}")
    print(f"  Payout ratio      {_fmt(cm.payout_ratio_pct, '%')}")
    print(f"  Trailing EPS      {_fmt(cm.trailing_eps)}")
    print(f"  Book value/share  {_fmt(cm.book_value_per_share)}")
    print(f"  52w high          {_fmt(cm.fifty_two_week_high)}")
    print(f"  52w low           {_fmt(cm.fifty_two_week_low)}")

    print("\n  ── Historical (newest first) ──")
    print(f"  {'Period':<12} {'FY-end Close':>12} {'EPS':>8} {'BVPS':>8} {'P/E':>8} {'P/B':>8}")
    for p in h.yearly:
        print(
            f"  {p.period_end!s:<12} {_fmt(p.fy_end_close_price):>12} "
            f"{_fmt(p.eps_for_year):>8} {_fmt(p.book_value_per_share):>8} "
            f"{_fmt(p.pe, '×'):>8} {_fmt(p.pb, '×'):>8}"
        )

    print(f"\n  Median P/E ({m.years_in_window}y): {_fmt(m.pe_median, '×')}  "
          f"(min {_fmt(m.pe_min, '×')}, max {_fmt(m.pe_max, '×')})")
    print(f"  Median P/B ({m.years_in_window}y): {_fmt(m.pb_median, '×')}  "
          f"(min {_fmt(m.pb_min, '×')}, max {_fmt(m.pb_max, '×')})")

    print(f"\n  ── Peers (available={r.peer_comparison.available}) ──")
    if r.peer_comparison.available:
        for p in r.peer_comparison.peers:
            print(f"    {p.ticker:<14} P/E {_fmt(p.pe, '×')}  P/B {_fmt(p.pb, '×')}")
    else:
        print(f"    {r.peer_comparison.note}")

    print(f"\n  ── Qualitative findings ({len(r.qualitative_assessment)}) ──\n")
    for i, finding in enumerate(r.qualitative_assessment, start=1):
        print(f"  [{i}] ({finding.category})")
        words = finding.claim.split()
        line = "      "
        for w in words:
            if len(line) + len(w) > 76:
                print(line)
                line = "      " + w
            else:
                line += (" " if line.strip() else "") + w
        if line.strip():
            print(line)
        for ev in finding.evidence:
            yrs = ", ".join(str(y) for y in ev.years_referenced)
            vals = ", ".join(f"{v:.2f}" if abs(v) < 1000 else f"{v:,.0f}" for v in ev.values)
            print(f"        evidence: {ev.metric}  [{yrs}] = [{vals}]")
        print()

    if r.data_quality_notes:
        print("  ── Data-quality notes ──")
        for note in r.data_quality_notes:
            print(f"  · {note}")

    print(f"\n  Disclaimer: {r.disclaimer[:80]}…")


async def main(tickers: list[str]) -> int:
    configure_logging("INFO")
    overall_ok = True
    for ticker in tickers:
        log.info("smoke.valuation.start", ticker=ticker)
        deps, stack = await build_agent_deps()
        try:
            try:
                report = await run_valuation_agent(ticker, deps)
            except Exception as exc:
                print(f"\n!! {ticker} failed: {exc}")
                overall_ok = False
                continue
        finally:
            await stack.aclose()
        _print_report(report)
        out_path = f"/tmp/valuation_{ticker.upper()}.json"
        with open(out_path, "w") as f:
            f.write(report.model_dump_json(indent=2))
        print(f"\n  Raw JSON written to {out_path}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    args = sys.argv[1:] or ["RELIANCE"]
    raise SystemExit(asyncio.run(main(args)))
