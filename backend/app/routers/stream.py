import asyncio
import json
from typing import Any

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["stream"])

# Global event bus — producers push events, SSE consumers read them
event_bus: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


async def publish_event(event_type: str, data: dict[str, Any]) -> None:
    """Push an event onto the bus for all SSE consumers."""
    await event_bus.put({"event": event_type, "data": data})


async def _event_generator():
    """Yield events from the bus as SSE messages."""
    while True:
        payload = await event_bus.get()
        yield {
            "event": payload["event"],
            "data": json.dumps(payload["data"]),
        }


@router.get("/api/v1/stream")
async def stream_events():
    return EventSourceResponse(_event_generator())
