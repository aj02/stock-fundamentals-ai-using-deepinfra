"""Live smoke runner for the Financials Agent.

Hits Anthropic for real. Pretty-prints the qualitative findings so we can
eyeball whether they read concrete or generic.

Usage (inside container with ANTHROPIC_API_KEY + REDIS_URL set):
    python -m scripts.smoke_financials_agent RELIANCE
    python -m scripts.smoke_financials_agent INFY HDFCBANK
"""

from __future__ import annotations

import asyncio
import json
import sys

import structlog

from app.agents.deps import build_agent_deps
from app.agents.financials import run_financials_agent
from app.core.logging import configure_logging
from app.schemas.agents import FinancialsReport

log = structlog.get_logger("smoke")


def _fmt_inr(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:,.1f} cr"
    return f"₹{value:,.0f}"


def _fmt_pct(value: float | None) -> str:
    return f"{value:.2f}%" if value is not None else "—"


def _fmt_ratio(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "—"


def _print_report(r: FinancialsReport) -> None:
    print(f"\n{'═' * 76}")
    print(f"  {r.company_name}  ({r.yfinance_symbol})")
    print(f"  {r.sector} / {r.industry} · {r.currency}")
    print(f"  Period: {r.period_summary}")
    print(f"{'═' * 76}\n")

    print("  ── Yearly data (newest first) ──")
    print(f"  {'Period':<12} {'Revenue':>14} {'Op Income':>13} {'Net Income':>13} {'OCF':>13} {'FCF':>13}")
    for row in r.yearly_data:
        print(
            f"  {row.period_end!s:<12} {_fmt_inr(row.revenue):>14} "
            f"{_fmt_inr(row.operating_income):>13} {_fmt_inr(row.net_income):>13} "
            f"{_fmt_inr(row.operating_cash_flow):>13} {_fmt_inr(row.free_cash_flow):>13}"
        )

    print("\n  ── Ratios (newest first) ──")
    print(
        f"  {'Period':<12} {'OpMgn%':>8} {'NetMgn%':>8} {'ROE%':>7} {'ROCE%':>7} "
        f"{'D/E':>6} {'OCF/PAT':>8} {'CurR':>6}"
    )
    for row in r.ratios.yearly:
        print(
            f"  {row.period_end!s:<12} {_fmt_pct(row.operating_margin_pct):>8} "
            f"{_fmt_pct(row.net_margin_pct):>8} {_fmt_pct(row.roe_pct):>7} "
            f"{_fmt_pct(row.roce_pct):>7} {_fmt_ratio(row.debt_to_equity):>6} "
            f"{_fmt_ratio(row.ocf_to_pat):>8} {_fmt_ratio(row.current_ratio):>6}"
        )

    g = r.ratios.growth
    print(
        f"\n  Revenue CAGR — 3y: {_fmt_pct(g.revenue_cagr_3y_pct)}  ·  "
        f"Net income CAGR — 3y: {_fmt_pct(g.net_income_cagr_3y_pct)}  ·  "
        f"FCF CAGR — 3y: {_fmt_pct(g.fcf_cagr_3y_pct)}"
    )

    print(f"\n  ── Qualitative findings ({len(r.qualitative_assessment)}) ──\n")
    for i, finding in enumerate(r.qualitative_assessment, start=1):
        print(f"  [{i}] ({finding.category})")
        # Wrap claim text at ~70 chars for readability.
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


async def run_one(ticker: str) -> FinancialsReport:
    deps, stack = await build_agent_deps()
    try:
        report = await run_financials_agent(ticker, deps)
    finally:
        await stack.aclose()
    return report


async def main(tickers: list[str]) -> int:
    configure_logging("INFO")
    overall_ok = True
    for ticker in tickers:
        log.info("smoke.start", ticker=ticker)
        try:
            report = await run_one(ticker)
        except Exception as exc:
            print(f"\n!! {ticker} failed: {exc}")
            overall_ok = False
            continue
        _print_report(report)

        # Also emit the raw JSON so we have the structured form on file.
        out_path = f"/tmp/financials_{ticker.upper()}.json"
        with open(out_path, "w") as f:
            f.write(report.model_dump_json(indent=2))
        print(f"\n  Raw JSON written to {out_path}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    args = sys.argv[1:] or ["RELIANCE"]
    raise SystemExit(asyncio.run(main(args)))
