"""Structlog configuration.

Single-line JSON logs to stdout, augmented with a `run_id` field whenever a
ContextVar is set. Each agent run sets `run_id_ctx` once and every log line
emitted for the duration of that run carries the correlation id.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

run_id_ctx: ContextVar[str | None] = ContextVar("run_id", default=None)


def _inject_run_id(_logger: Any, _method: str, event: dict[str, Any]) -> dict[str, Any]:
    rid = run_id_ctx.get()
    if rid is not None:
        event["run_id"] = rid
    return event


def configure_logging(level: str = "INFO") -> None:
    """Idempotently configure stdlib + structlog for JSON output."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level, logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _inject_run_id,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


__all__ = ["configure_logging", "run_id_ctx"]
