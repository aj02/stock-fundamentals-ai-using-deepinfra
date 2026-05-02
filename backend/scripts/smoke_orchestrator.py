"""Live smoke runner for the full orchestrator (steps 7+8+9 together).

Hits Anthropic ~5 times (Financials + Valuation + Management + Risk +
Thesis). May download the annual report on first run.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

import structlog

from app.agents.deps import build_agent_deps
from app.agents.events import RunEvent
from app.agents.orchestrator import run_analysis
from app.core.logging import configure_logging
from app.schemas.run import RunReport

log = structlog.get_logger("smoke")


def _print_event(ev: RunEvent) -> None:
    name = type(ev).__name__
    extras = ev.model_dump(exclude={"type", "run_id", "timestamp"})
    print(f"  ▸ {name:<22}  {extras}")


def _print_report(r: RunReport) -> None:
    print(f"\n{'═' * 76}")
    print(f"  Run {r.run_id}  •  {r.ticker}  •  depth={r.depth}  •  status={r.status}")
    print(f"  duration: {r.duration_seconds}s")
    print(f"{'═' * 76}")

    if r.financials:
        print(f"  Financials: {len(r.financials.qualitative_assessment)} findings")
    if r.valuation:
        print(f"  Valuation: {len(r.valuation.qualitative_assessment)} findings  "
              f"(P/E {r.valuation.current_multiples.trailing_pe})")
    if r.management:
        print(f"  Management: {len(r.management.mda_findings)} MD&A + "
              f"{len(r.management.governance_findings)} gov findings  "
              f"(FY{r.management.fiscal_year})")
    if r.risk:
        print(f"  Risk: {len(r.risk.risks)} risks  "
              f"(screener_concerns_used={r.risk.screener_concerns_used})")

    if r.thesis:
        print(f"\n  ── Bull case ({len(r.thesis.bull_case)}) ──")
        for i, p in enumerate(r.thesis.bull_case, 1):
            print(f"  [{i}] {p.point}")
            for c in p.citations:
                print(f"        ↳ {c.source_agent}[{c.finding_index}]: {c.summary}")
            print()
        print(f"  ── Bear case ({len(r.thesis.bear_case)}) ──")
        for i, p in enumerate(r.thesis.bear_case, 1):
            print(f"  [{i}] {p.point}")
            for c in p.citations:
                print(f"        ↳ {c.source_agent}[{c.finding_index}]: {c.summary}")
            print()
        print("  ── Neutral summary ──")
        print(f"  {r.thesis.neutral_summary}")
        if r.thesis.sections_unavailable:
            print(f"\n  Sections unavailable in thesis: {r.thesis.sections_unavailable}")

    if r.unavailable_sections:
        print("\n  ── Unavailable sections ──")
        for u in r.unavailable_sections:
            print(f"  · {u.section}: {u.reason[:120]}")


async def main(args: list[str]) -> int:
    configure_logging("INFO")
    ticker = args[0] if args else "RELIANCE"
    depth = args[1] if len(args) > 1 else "full"

    deps, stack = await build_agent_deps()
    try:
        try:
            print(f"\nStarting {depth} analysis of {ticker}…\n")
            run_id = str(uuid.uuid4())
            report = await run_analysis(
                run_id=run_id, ticker=ticker, depth=depth,  # type: ignore[arg-type]
                deps=deps, on_event=_print_event,
            )
        except Exception as exc:
            print(f"\n!! orchestrator failed: {exc!r}")
            return 1
    finally:
        await stack.aclose()

    _print_report(report)
    out_path = f"/tmp/run_{ticker.upper()}_{report.run_id[:8]}.json"
    with open(out_path, "w") as f:
        f.write(report.model_dump_json(indent=2))
    print(f"\n  Raw JSON written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
