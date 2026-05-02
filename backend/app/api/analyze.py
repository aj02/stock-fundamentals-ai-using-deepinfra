"""POST /analyze + GET /runs/{run_id} + DELETE /runs/{run_id} + cancel-all.

Default behaviour (cache-first):
  POST /analyze {"ticker":"RELIANCE","depth":"full"} returns the most recent
  completed run for that ticker if it is younger than CACHE_TTL_REPORT_SECONDS
  (12h by default). No new agent calls fire. Pass {"force_refresh":true} to
  trigger a fresh orchestrator run anyway.

Cancellation:
  DELETE /runs/{run_id}     — cancel one in-flight run (no-op if completed).
  POST   /runs/cancel-all   — cancel every in-flight run on this process.

Per spec, every API response carries a top-level `disclaimer` field.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.deps import build_agent_deps
from app.agents.events import RunEvent
from app.agents.orchestrator import run_analysis
from app.core.config import DISCLAIMER, get_settings
from app.schemas.run import RunReport
from app.services import runs_repo
from app.services.event_bus import get_event_bus
from app.services.run_registry import get_run_registry

router = APIRouter(tags=["analyze"])
log = structlog.get_logger(__name__)


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=24, examples=["RELIANCE"])
    depth: Literal["quick", "full"] = "full"
    force_refresh: bool = Field(
        default=False,
        description=(
            "If false (default), returns the most recent completed run for "
            "this ticker when one exists within the cache TTL. Set true to "
            "always trigger a fresh orchestrator run."
        ),
    )


class AnalyzeResponse(BaseModel):
    run_id: str
    websocket_url: str
    status_url: str
    cached: bool = Field(
        default=False,
        description="True if a previously-completed run is being returned and no agents were re-run.",
    )
    disclaimer: str = Field(default=DISCLAIMER)


class RunFetchResponse(BaseModel):
    run_id: str
    report: RunReport
    disclaimer: str = Field(default=DISCLAIMER)


class CancelResponse(BaseModel):
    cancelled: list[str]
    disclaimer: str = Field(default=DISCLAIMER)


async def _execute_run(run_id: str, ticker: str, depth: Literal["quick", "full"]) -> None:
    """Background coroutine: run the orchestrator + persist the report."""
    bus = get_event_bus()

    async def _on_event(event: RunEvent) -> None:
        await bus.publish(run_id, event)

    deps, stack = await build_agent_deps()
    try:
        try:
            report = await run_analysis(
                run_id=run_id, ticker=ticker, depth=depth,
                deps=deps, on_event=_on_event,
            )
        except asyncio.CancelledError:
            # The orchestrator catches CancelledError internally and returns
            # a 'cancelled' RunReport, so we shouldn't see it here. But if a
            # cancellation lands DURING build_agent_deps or before, persist
            # a minimal cancelled record so the row isn't stuck on 'queued'.
            log.info("analyze.cancelled_outside_orchestrator", run_id=run_id)
            report = RunReport(
                run_id=run_id, ticker=ticker.upper(), depth=depth,
                status="cancelled",
                started_at=datetime.now(UTC), completed_at=datetime.now(UTC),
                duration_seconds=0.0, error="Cancelled before orchestrator started.",
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("analyze.background_run_failed", run_id=run_id)
            report = RunReport(
                run_id=run_id, ticker=ticker.upper(), depth=depth,
                status="failed",
                started_at=datetime.now(UTC), completed_at=datetime.now(UTC),
                duration_seconds=0.0, error=f"{type(exc).__name__}: {exc}",
            )
    finally:
        await stack.aclose()

    try:
        await runs_repo.update_run_completed(run_id, report)
    except Exception as exc:  # noqa: BLE001
        log.warning("analyze.persist_failed", run_id=run_id, error=str(exc))

    await bus.mark_complete(run_id)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Start (or return cached) analysis run for a ticker.",
)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    settings = get_settings()
    ticker_u = req.ticker.upper()

    # Cache-first: when force_refresh=False, look up the latest completed
    # run for this ticker within the configured TTL.
    if not req.force_refresh:
        cached_id = await runs_repo.fetch_latest_run_id_for_ticker(
            ticker_u, max_age_seconds=settings.CACHE_TTL_REPORT_SECONDS
        )
        if cached_id is not None:
            log.info("analyze.cache_hit", ticker=ticker_u, run_id=cached_id)
            return AnalyzeResponse(
                run_id=cached_id,
                websocket_url=f"/ws/runs/{cached_id}",
                status_url=f"/runs/{cached_id}",
                cached=True,
            )

    run_id = str(uuid.uuid4())
    log.info("analyze.start_fresh", run_id=run_id, ticker=ticker_u, depth=req.depth)

    try:
        await runs_repo.create_run(run_id, ticker_u, req.depth)
    except Exception as exc:  # noqa: BLE001
        log.warning("analyze.create_run_failed", run_id=run_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not register run: {exc}",
        ) from exc

    # Spawn the orchestrator on the running event loop. We register the task
    # in the run-registry so DELETE /runs/{run_id} can cancel it.
    task = asyncio.create_task(_execute_run(run_id, req.ticker, req.depth))
    await get_run_registry().register(run_id, task)

    return AnalyzeResponse(
        run_id=run_id,
        websocket_url=f"/ws/runs/{run_id}",
        status_url=f"/runs/{run_id}",
        cached=False,
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunFetchResponse,
    summary="Fetch a previously-completed RunReport.",
)
async def fetch_run(run_id: str) -> RunFetchResponse:
    report = await runs_repo.fetch_run(run_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run {run_id} not found or still in progress",
        )
    return RunFetchResponse(run_id=run_id, report=report)


@router.delete(
    "/runs/{run_id}",
    response_model=CancelResponse,
    summary="Cancel an in-flight run. No-op if already completed.",
)
async def cancel_run(run_id: str) -> CancelResponse:
    cancelled = await get_run_registry().cancel(run_id)
    if cancelled:
        log.info("analyze.cancel_ok", run_id=run_id)
        return CancelResponse(cancelled=[run_id])
    return CancelResponse(cancelled=[])


@router.post(
    "/runs/cancel-all",
    response_model=CancelResponse,
    summary="Cancel every in-flight run on this backend (kill switch).",
)
async def cancel_all() -> CancelResponse:
    ids = await get_run_registry().cancel_all()
    log.info("analyze.cancel_all", count=len(ids))
    return CancelResponse(cancelled=ids)


@router.get(
    "/runs",
    summary="List active in-flight runs (for the kill switch UI).",
)
async def list_active_runs() -> dict[str, list[str] | str]:
    ids = await get_run_registry().active_run_ids()
    return {"active_run_ids": ids, "disclaimer": DISCLAIMER}
