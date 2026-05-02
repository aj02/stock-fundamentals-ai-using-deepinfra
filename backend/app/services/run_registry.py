"""Process-wide registry of in-flight orchestrator tasks.

Lets the API layer cancel a specific run (or every active run) by `run_id`.
The orchestrator catches `CancelledError`, marks the DB row as 'cancelled',
and unwinds — no more LLM calls fire after `task.cancel()` resolves.

Single-replica only. Multi-replica deployments would need Redis pub/sub
for cross-process cancellation.
"""

from __future__ import annotations

import asyncio

import structlog

log = structlog.get_logger(__name__)


class RunRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def register(self, run_id: str, task: asyncio.Task) -> None:
        async with self._lock:
            self._tasks[run_id] = task
        # Auto-clean on completion so we don't leak stopped tasks.
        task.add_done_callback(lambda _t, rid=run_id: self._cleanup(rid))

    def _cleanup(self, run_id: str) -> None:
        # add_done_callback fires synchronously from the loop; pop is safe.
        self._tasks.pop(run_id, None)

    async def cancel(self, run_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(run_id)
        if task is None or task.done():
            return False
        log.info("run_registry.cancel", run_id=run_id)
        task.cancel()
        return True

    async def cancel_all(self) -> list[str]:
        async with self._lock:
            ids = [rid for rid, t in self._tasks.items() if not t.done()]
            tasks = [self._tasks[rid] for rid in ids]
        log.info("run_registry.cancel_all", count=len(ids))
        for t in tasks:
            t.cancel()
        return ids

    async def active_run_ids(self) -> list[str]:
        async with self._lock:
            return [rid for rid, t in self._tasks.items() if not t.done()]


_REGISTRY: RunRegistry | None = None


def get_run_registry() -> RunRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = RunRegistry()
    return _REGISTRY
