"""Event types streamed over WebSocket for live UI updates.

The orchestrator emits these via an async callback. Step 8 collects
them in memory and returns the final RunReport synchronously; step 10
wires the same callback to a WebSocket so the frontend can render
agent progress in real-time.

Event design notes:
- One event class per event type, all share a common base.
- All carry `run_id` + `timestamp` so they can be correlated and
  reordered if the network jitter reorders them.
- `payload` is intentionally typed loosely — Pydantic does the
  serialisation per concrete event subclass.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EventType = Literal[
    "run_started",
    "agent_queued",
    "agent_started",
    "tool_called",
    "tool_completed",
    "agent_completed",
    "agent_failed",
    "thesis_started",
    "thesis_completed",
    "run_completed",
    "run_failed",
]

AgentName = Literal[
    "coordinator", "financials", "valuation", "management", "risk", "thesis"
]


class _BaseEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: EventType
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunStartedEvent(_BaseEvent):
    type: Literal["run_started"] = "run_started"
    ticker: str
    depth: Literal["quick", "full"]
    agents_planned: list[AgentName]


class AgentQueuedEvent(_BaseEvent):
    type: Literal["agent_queued"] = "agent_queued"
    agent: AgentName


class AgentStartedEvent(_BaseEvent):
    type: Literal["agent_started"] = "agent_started"
    agent: AgentName


class ToolCalledEvent(_BaseEvent):
    type: Literal["tool_called"] = "tool_called"
    agent: AgentName
    tool_name: str
    args_summary: str | None = None


class ToolCompletedEvent(_BaseEvent):
    type: Literal["tool_completed"] = "tool_completed"
    agent: AgentName
    tool_name: str
    duration_ms: int | None = None


class AgentCompletedEvent(_BaseEvent):
    type: Literal["agent_completed"] = "agent_completed"
    agent: AgentName
    duration_seconds: float
    findings_count: int | None = None


class AgentFailedEvent(_BaseEvent):
    type: Literal["agent_failed"] = "agent_failed"
    agent: AgentName
    error: str


class ThesisStartedEvent(_BaseEvent):
    type: Literal["thesis_started"] = "thesis_started"
    sections_available: list[AgentName]
    sections_unavailable: list[AgentName]


class ThesisCompletedEvent(_BaseEvent):
    type: Literal["thesis_completed"] = "thesis_completed"
    bull_points: int
    bear_points: int


class RunCompletedEvent(_BaseEvent):
    type: Literal["run_completed"] = "run_completed"
    duration_seconds: float
    sections_completed: list[AgentName]
    sections_unavailable: list[AgentName]


class RunFailedEvent(_BaseEvent):
    type: Literal["run_failed"] = "run_failed"
    error: str


# Discriminated union of all events for typed serialisation.
RunEvent = (
    RunStartedEvent
    | AgentQueuedEvent
    | AgentStartedEvent
    | ToolCalledEvent
    | ToolCompletedEvent
    | AgentCompletedEvent
    | AgentFailedEvent
    | ThesisStartedEvent
    | ThesisCompletedEvent
    | RunCompletedEvent
    | RunFailedEvent
)


# Callback signature the orchestrator accepts. In step 8 it's a list-append
# closure; in step 10 it's a coroutine that pushes onto a WebSocket queue.
EventCallback = Any  # Callable[[RunEvent], Awaitable[None] | None]
