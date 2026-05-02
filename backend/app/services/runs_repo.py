"""Persistence for analysis runs.

Stores one row per run in `runs` (created when the run is queued, updated
on completion). The full `RunReport` JSON is written to a JSONB column so
GET /runs/{run_id} can return it without re-running the agents.

We use raw SQL via SQLAlchemy core because the schema is small enough that
the ORM overhead isn't worth it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import text

from app.core.db import SessionLocal
from app.schemas.run import RunReport

log = structlog.get_logger(__name__)


async def create_run(run_id: str, ticker: str, depth: str) -> None:
    async with SessionLocal() as s:
        await s.execute(
            text(
                "INSERT INTO runs (id, ticker, depth, status, created_at) "
                "VALUES (:id, :ticker, :depth, 'queued', :created_at)"
            ),
            {"id": run_id, "ticker": ticker, "depth": depth, "created_at": datetime.now(UTC)},
        )
        await s.commit()


async def update_run_completed(run_id: str, report: RunReport) -> None:
    async with SessionLocal() as s:
        await s.execute(
            text(
                "UPDATE runs "
                "SET status = :status, completed_at = :completed_at, "
                "    report = cast(:report AS jsonb), error = :error "
                "WHERE id = :id"
            ),
            {
                "id": run_id,
                "status": report.status,
                "completed_at": report.completed_at or datetime.now(UTC),
                "report": report.model_dump_json(),
                "error": report.error,
            },
        )
        await s.commit()


async def fetch_run(run_id: str) -> RunReport | None:
    async with SessionLocal() as s:
        result = await s.execute(
            text("SELECT report FROM runs WHERE id = :id"),
            {"id": run_id},
        )
        row = result.first()
        if row is None or row[0] is None:
            return None
        report_raw = row[0]
        # asyncpg returns JSONB as a Python dict already, but be tolerant.
        if isinstance(report_raw, str):
            return RunReport.model_validate_json(report_raw)
        return RunReport.model_validate(report_raw)


async def fetch_latest_run_id_for_ticker(
    ticker: str, max_age_seconds: int
) -> str | None:
    """Return the run_id of the most recent COMPLETED run for `ticker`
    whose `completed_at` is within `max_age_seconds`. Cancelled and failed
    runs are not returned — callers want a cache hit only when the report
    is actually populated.
    """
    async with SessionLocal() as s:
        result = await s.execute(
            text(
                "SELECT id FROM runs "
                "WHERE ticker = :ticker "
                "  AND status = 'completed' "
                "  AND completed_at >= now() - (:max_age || ' seconds')::interval "
                "ORDER BY completed_at DESC "
                "LIMIT 1"
            ),
            {"ticker": ticker.upper(), "max_age": str(max_age_seconds)},
        )
        row = result.first()
        return str(row[0]) if row is not None else None
