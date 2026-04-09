"""SSE (Server-Sent Events) endpoint for real-time dashboard updates.

Uses a broadcast pattern so every connected client receives every event.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["stream"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Broadcast hub — supports multiple simultaneous SSE consumers
# ---------------------------------------------------------------------------

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_lock = asyncio.Lock()

HEARTBEAT_INTERVAL_SECONDS = 15


async def publish_event(event_type: str, data: dict[str, Any]) -> None:
    """Broadcast an event to every connected SSE client."""
    payload = {
        "event": event_type,
        "data": {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    async with _lock:
        dead: list[asyncio.Queue] = []
        for q in _subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _subscribers.discard(q)
            logger.warning("SSE: dropped slow consumer")


async def _subscribe() -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
    async with _lock:
        _subscribers.add(q)
    return q


async def _unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    async with _lock:
        _subscribers.discard(q)


async def _event_generator():
    """Yield events from a per-client queue, with periodic heartbeats."""
    q = await _subscribe()
    try:
        while True:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL_SECONDS)
                yield {
                    "event": payload["event"],
                    "data": json.dumps(payload["data"]),
                }
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "type": "heartbeat",
                        "data": {},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }),
                }
    finally:
        await _unsubscribe(q)


@router.get("/api/v1/stream")
async def stream_events():
    return EventSourceResponse(_event_generator())
