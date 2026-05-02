"""Coordinator (orchestrator).

NOT a PydanticAI agent — plain async Python. Responsibilities:
  - Accept a ticker + depth + an event callback.
  - Validate the ticker exists on NSE/BSE (best-effort: yfinance fetch must
    succeed for the orchestrator to proceed; this is also the canonical
    cache warming step for everything that follows).
  - Run the four parallel agents via `asyncio.gather(return_exceptions=True)`.
    Per-agent failures are caught — they don't poison the rest of the run.
  - Run the Thesis Agent on whatever DID succeed.
  - Stream events to the supplied callback as agents progress.
  - Return a `RunReport` with all assembled outputs and explicit
    `unavailable_sections` markers for partial failures.

This is intentionally orchestration-as-code: ~50 lines of asyncio.gather
that you can read top-to-bottom in one sitting.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog

from app.agents.deps import AgentDeps
from app.agents.events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentQueuedEvent,
    AgentStartedEvent,
    AgentName,
    RunCompletedEvent,
    RunEvent,
    RunFailedEvent,
    RunStartedEvent,
    ThesisCompletedEvent,
    ThesisStartedEvent,
)
from app.agents.financials import run_financials_agent
from app.agents.management import run_management_agent
from app.agents.risk import run_risk_agent
from app.agents.thesis import run_thesis_agent
from app.agents.valuation import run_valuation_agent
from app.core.logging import run_id_ctx
from app.schemas.agents import FinancialsReport
from app.schemas.management import ManagementReport
from app.schemas.risk import RiskReport
from app.schemas.run import RunDepth, RunReport, SectionUnavailable
from app.schemas.thesis import InvestmentThesis
from app.schemas.valuation import ValuationReport

log = structlog.get_logger(__name__)

# Type alias — the runtime accepts both sync and async callbacks for ergonomics.
EventCallback = Callable[[RunEvent], Awaitable[None] | None]


def _agents_for_depth(depth: RunDepth) -> list[AgentName]:
    if depth == "quick":
        return ["financials", "valuation"]
    return ["financials", "valuation", "management", "risk"]


async def _emit(callback: EventCallback | None, event: RunEvent) -> None:
    if callback is None:
        return
    try:
        result = callback(event)
        if inspect.isawaitable(result):
            await result
    except Exception as exc:  # noqa: BLE001
        # Event emission must never break the run.
        log.warning("orchestrator.event_emit_failed", error=str(exc))


async def _run_one_agent(
    name: AgentName,
    coro_factory: Callable[[], Awaitable[Any]],
    callback: EventCallback | None,
    run_id: str,
) -> tuple[AgentName, Any | None, str | None, float]:
    """Run a single agent, emit start/end events, return (name, result|None, error|None, seconds)."""
    started = datetime.now(UTC)
    await _emit(callback, AgentStartedEvent(run_id=run_id, agent=name))
    try:
        result = await coro_factory()
        elapsed = (datetime.now(UTC) - started).total_seconds()
        findings_count = _count_findings(name, result)
        await _emit(
            callback,
            AgentCompletedEvent(
                run_id=run_id,
                agent=name,
                duration_seconds=round(elapsed, 2),
                findings_count=findings_count,
            ),
        )
        log.info(
            "orchestrator.agent_completed",
            agent=name,
            seconds=round(elapsed, 2),
            findings=findings_count,
        )
        return name, result, None, elapsed
    except asyncio.CancelledError:
        # Re-raise so asyncio.gather propagates the cancellation. Don't
        # mark this agent as "failed" — that would imply an error.
        raise
    except Exception as exc:  # noqa: BLE001
        elapsed = (datetime.now(UTC) - started).total_seconds()
        err = f"{type(exc).__name__}: {exc}"
        await _emit(callback, AgentFailedEvent(run_id=run_id, agent=name, error=err))
        log.warning("orchestrator.agent_failed", agent=name, error=err)
        return name, None, err, elapsed


def _count_findings(agent: AgentName, result: Any) -> int | None:
    if agent == "financials" and isinstance(result, FinancialsReport):
        return len(result.qualitative_assessment)
    if agent == "valuation" and isinstance(result, ValuationReport):
        return len(result.qualitative_assessment)
    if agent == "management" and isinstance(result, ManagementReport):
        return len(result.mda_findings) + len(result.governance_findings)
    if agent == "risk" and isinstance(result, RiskReport):
        return len(result.risks)
    return None


async def run_analysis(
    *,
    run_id: str,
    ticker: str,
    depth: RunDepth,
    deps: AgentDeps,
    on_event: EventCallback | None = None,
) -> RunReport:
    """The whole orchestration in one async function. ~50 lines if you
    squint past the event emission.

    Cancellation: if `task.cancel()` fires (e.g. via DELETE /runs/{id}),
    `asyncio.CancelledError` propagates out of the agent calls. We catch
    it at the top level, mark the report as `cancelled`, and re-raise
    so the surrounding background task tears down cleanly.
    """
    started_at = datetime.now(UTC)
    run_id_ctx.set(run_id)
    ticker_u = ticker.upper()
    agents_planned = _agents_for_depth(depth) + ["thesis"]

    try:
        return await _run_analysis_inner(
            run_id=run_id,
            ticker=ticker_u,
            depth=depth,
            deps=deps,
            on_event=on_event,
            started_at=started_at,
            agents_planned=agents_planned,
        )
    except asyncio.CancelledError:
        log.info("orchestrator.cancelled", run_id=run_id)
        completed_at = datetime.now(UTC)
        duration = (completed_at - started_at).total_seconds()
        await _emit(
            on_event,
            RunFailedEvent(run_id=run_id, error="Run cancelled by user."),
        )
        # Return a report shape rather than re-raising so the surrounding
        # background task can persist the 'cancelled' status.
        return RunReport(
            run_id=run_id,
            ticker=ticker_u,
            depth=depth,
            status="cancelled",
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=round(duration, 2),
            error="Cancelled by user.",
        )


async def _run_analysis_inner(
    *,
    run_id: str,
    ticker: str,
    depth: RunDepth,
    deps: AgentDeps,
    on_event: EventCallback | None,
    started_at: datetime,
    agents_planned: list[AgentName],
) -> RunReport:
    ticker_u = ticker
    await _emit(
        on_event,
        RunStartedEvent(run_id=run_id, ticker=ticker_u, depth=depth, agents_planned=agents_planned),
    )
    for a in agents_planned:
        await _emit(on_event, AgentQueuedEvent(run_id=run_id, agent=a))

    # Validate ticker by warming the yfinance financials cache. If this
    # fails, abort early — none of the agents can produce useful output.
    try:
        await deps.yfinance_client.fetch_financials(ticker_u)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        err = f"Ticker validation failed: {type(exc).__name__}: {exc}"
        await _emit(on_event, RunFailedEvent(run_id=run_id, error=err))
        return RunReport(
            run_id=run_id, ticker=ticker_u, depth=depth, status="failed",
            started_at=started_at, completed_at=datetime.now(UTC),
            duration_seconds=(datetime.now(UTC) - started_at).total_seconds(),
            error=err,
        )

    # Build the agent set + parallel coroutines.
    agent_coros: dict[AgentName, Callable[[], Awaitable[Any]]] = {
        "financials": lambda: run_financials_agent(ticker_u, deps),
        "valuation": lambda: run_valuation_agent(ticker_u, deps),
    }
    if depth == "full":
        agent_coros["management"] = lambda: run_management_agent(ticker_u, deps)
        agent_coros["risk"] = lambda: run_risk_agent(ticker_u, deps)

    parallel_tasks = [
        _run_one_agent(name, factory, on_event, run_id)
        for name, factory in agent_coros.items()
    ]
    results: list[tuple[AgentName, Any | None, str | None, float]] = await asyncio.gather(
        *parallel_tasks
    )

    # Sort outputs by agent name for the report assembly.
    fin: FinancialsReport | None = None
    val: ValuationReport | None = None
    mgmt: ManagementReport | None = None
    risk: RiskReport | None = None
    unavailable: list[SectionUnavailable] = []
    for name, result, error, _elapsed in results:
        if error is not None:
            unavailable.append(SectionUnavailable(section=name, reason=error))
            continue
        if name == "financials":
            fin = result
        elif name == "valuation":
            val = result
        elif name == "management":
            mgmt = result
        elif name == "risk":
            risk = result

    # Run Thesis on whatever survived. If literally everything failed, skip
    # and mark the run failed.
    thesis: InvestmentThesis | None = None
    available_for_thesis: list[AgentName] = [
        n for n, r in (("financials", fin), ("valuation", val), ("management", mgmt), ("risk", risk))
        if r is not None
    ]
    unavailable_for_thesis: list[AgentName] = [
        n for n, r in (("financials", fin), ("valuation", val), ("management", mgmt), ("risk", risk))
        if r is None and n in agent_coros  # only count agents that were ATTEMPTED
    ]

    if available_for_thesis:
        await _emit(
            on_event,
            ThesisStartedEvent(
                run_id=run_id,
                sections_available=available_for_thesis,
                sections_unavailable=unavailable_for_thesis,
            ),
        )
        try:
            thesis = await run_thesis_agent(
                ticker_u, deps, fin=fin, val=val, mgmt=mgmt, risk=risk
            )
            await _emit(
                on_event,
                ThesisCompletedEvent(
                    run_id=run_id,
                    bull_points=len(thesis.bull_case),
                    bear_points=len(thesis.bear_case),
                ),
            )
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
            unavailable.append(SectionUnavailable(section="thesis", reason=err))
            await _emit(on_event, AgentFailedEvent(run_id=run_id, agent="thesis", error=err))
            log.warning("orchestrator.thesis_failed", error=err)
    else:
        unavailable.append(
            SectionUnavailable(section="thesis", reason="No prior agent produced a usable report.")
        )

    completed_at = datetime.now(UTC)
    duration = (completed_at - started_at).total_seconds()
    sections_completed = [
        n for n, r in (
            ("financials", fin), ("valuation", val),
            ("management", mgmt), ("risk", risk),
        ) if r is not None
    ]
    if thesis is not None:
        sections_completed.append("thesis")

    await _emit(
        on_event,
        RunCompletedEvent(
            run_id=run_id,
            duration_seconds=round(duration, 2),
            sections_completed=sections_completed,
            sections_unavailable=[u.section for u in unavailable],
        ),
    )

    return RunReport(
        run_id=run_id,
        ticker=ticker_u,
        depth=depth,
        status="completed" if sections_completed else "failed",
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=round(duration, 2),
        financials=fin,
        valuation=val,
        management=mgmt,
        risk=risk,
        thesis=thesis,
        unavailable_sections=unavailable,
    )
