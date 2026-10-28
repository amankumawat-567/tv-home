"""Broadcasts server events (state changes, toasts, the running-app marker) to
every connected WebSocket client — see routes/state.py's `/api/events`."""
import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict[str, Any]) -> None:
        for q in list(self._subscribers):
            q.put_nowait(event)


bus = EventBus()


def publish_state(state: dict[str, Any]) -> None:
    bus.publish({"type": "state", "data": state})


def publish_toast(message: str, tone: str = "info") -> None:
    bus.publish({"type": "toast", "data": {"id": f"srv{id(message)}", "message": message, "tone": tone}})


def publish_running(app: dict[str, Any] | None) -> None:
    bus.publish({"type": "running", "data": app})
