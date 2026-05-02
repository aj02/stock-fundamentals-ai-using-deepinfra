"""Live smoke runner for the Management Agent (step 6).

Will hit Anthropic AND will download the latest annual-report PDF from BSE
on first run (subsequently cached on disk).
"""

from __future__ import annotations

import asyncio
import sys

import structlog

from app.agents.deps import build_agent_deps
from app.agents.management import run_management_agent
from app.core.logging import configure_logging
from app.schemas.management import ManagementReport

log = structlog.get_logger("smoke")


def _print_report(r: ManagementReport) -> None:
    print(f"\n{'═' * 76}")
    print(f"  {r.company_name}  ({r.yfinance_symbol})")
    print(f"  Annual Report: FY{r.fiscal_year}  ({r.annual_report_page_count} pages)")
    print(f"  Source: {r.annual_report_url}")
    print(f"{'═' * 76}")

    def _print_section(title: str, findings: list) -> None:  # type: ignore[type-arg]
        print(f"\n  ── {title} ({len(findings)} findings) ──\n")
        for i, finding in enumerate(findings, start=1):
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
                quote = ev.quote
                if len(quote) > 200:
                    quote = quote[:200] + "…"
                page = f"p.{ev.page}" if ev.page else "—"
                print(f'        [{ev.section}/{page}] "{quote}"')
            print()

    _print_section("MD&A findings", r.mda_findings)
    _print_section("Governance findings", r.governance_findings)

    if r.data_quality_notes:
        print("  ── Data-quality notes ──")
        for note in r.data_quality_notes:
            print(f"  · {note}")

    print(f"\n  Disclaimer: {r.disclaimer[:80]}…")


async def main(tickers: list[str]) -> int:
    configure_logging("INFO")
    overall_ok = True
    for ticker in tickers:
        log.info("smoke.management.start", ticker=ticker)
        deps, stack = await build_agent_deps()
        try:
            try:
                report = await run_management_agent(ticker, deps)
            except Exception as exc:
                print(f"\n!! {ticker} failed: {exc!r}")
                overall_ok = False
                continue
        finally:
            await stack.aclose()
        _print_report(report)
        out_path = f"/tmp/management_{ticker.upper()}.json"
        with open(out_path, "w") as f:
            f.write(report.model_dump_json(indent=2))
        print(f"\n  Raw JSON written to {out_path}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    args = sys.argv[1:] or ["RELIANCE"]
    raise SystemExit(asyncio.run(main(args)))
