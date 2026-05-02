"""In-process pub/sub for run events.

Single-replica only. Real production would use Redis pub/sub, but the
showcase boots one backend container; this is sufficient and removes a
moving part.

Subscribers always replay history then receive new events live, so a UI
that connects mid-run still gets the timeline it missed. When the run
publishes a sentinel (None), all subscribers' queues are closed.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

import structlog

from app.agents.events import RunEvent

log = structlog.get_logger(__name__)

# Sentinel pushed onto subscriber queues when the run completes.
_SENTINEL: object = object()


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._history: dict[str, list[RunEvent]] = defaultdict(list)
        self._completed: set[str] = set()
        self._lock = asyncio.Lock()

    async def publish(self, run_id: str, event: RunEvent) -> None:
        async with self._lock:
            self._history[run_id].append(event)
            queues = list(self._queues.get(run_id, []))
        for q in queues:
            await q.put(event)

    async def mark_complete(self, run_id: str) -> None:
        """Tell all subscribers the run is over and stop accepting more
        subscribers (any new subscribe() will return history + closed queue).
        """
        async with self._lock:
            self._completed.add(run_id)
            queues = list(self._queues.get(run_id, []))
        for q in queues:
            await q.put(_SENTINEL)
        log.debug("event_bus.run_completed", run_id=run_id, subscribers=len(queues))

    async def subscribe(
        self, run_id: str
    ) -> tuple[list[RunEvent], asyncio.Queue, bool]:
        """Return (history, live_queue, already_completed).

        - history: every event published before this call.
        - live_queue: receives any event published from now on, terminating
          with _SENTINEL when mark_complete is called. Empty if already_completed.
        - already_completed: True if the run is finished.
        """
        async with self._lock:
            history = list(self._history.get(run_id, []))
            already_completed = run_id in self._completed
            q: asyncio.Queue = asyncio.Queue()
            if not already_completed:
                self._queues[run_id].append(q)
        return history, q, already_completed

    async def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        async with self._lock:
            self._queues.get(run_id, []).remove(q)

    @staticmethod
    def is_sentinel(item: object) -> bool:
        return item is _SENTINEL


# Process-wide singleton.
_BUS: EventBus | None = None


def get_event_bus() -> EventBus:
    global _BUS
    if _BUS is None:
        _BUS = EventBus()
    return _BUS
