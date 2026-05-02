"""WebSocket endpoint for live run events.

Client connects to /ws/runs/{run_id} after POST /analyze. We replay any
events that already happened, then stream new ones as the orchestrator
publishes them. When the run completes, the bus publishes a sentinel and
we close the WebSocket cleanly.
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import EventBus, get_event_bus

router = APIRouter()
log = structlog.get_logger(__name__)


@router.websocket("/ws/runs/{run_id}")
async def run_events(ws: WebSocket, run_id: str) -> None:
    await ws.accept()
    bus: EventBus = get_event_bus()
    history, queue, already_completed = await bus.subscribe(run_id)

    log.info(
        "ws.connected",
        run_id=run_id,
        history_size=len(history),
        already_completed=already_completed,
    )

    try:
        # Replay history first so a UI that connects mid-run still sees the
        # full timeline.
        for event in history:
            await ws.send_json(event.model_dump(mode="json"))

        if already_completed:
            await ws.close(code=1000, reason="Run already completed")
            return

        # Live stream — receive events from the queue and forward.
        while True:
            item = await queue.get()
            if EventBus.is_sentinel(item):
                break
            await ws.send_json(item.model_dump(mode="json"))

        await ws.close(code=1000, reason="Run completed")
    except WebSocketDisconnect:
        log.info("ws.disconnected", run_id=run_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("ws.error", run_id=run_id, error=str(exc))
        try:
            await ws.close(code=1011, reason=f"Internal error: {type(exc).__name__}")
        except Exception:  # noqa: BLE001
            pass
    finally:
        await bus.unsubscribe(run_id, queue)
