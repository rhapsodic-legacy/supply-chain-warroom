"""Real-time event streaming — WebSocket (primary) with SSE fallback.

Uses a unified broadcast hub so every connected client (WS or SSE) receives
every event.  Clients that support WebSocket get bidirectional messaging;
environments that don't (e.g. some proxies) fall back to SSE transparently.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["stream"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unified broadcast hub — supports both WebSocket and SSE consumers
# ---------------------------------------------------------------------------

HEARTBEAT_INTERVAL_SECONDS = 15


class _TransportKind(str, Enum):
    SSE = "sse"
    WS = "ws"


class _Subscriber:
    """Wraps either an asyncio.Queue (SSE) or a WebSocket connection."""

    __slots__ = ("kind", "queue", "ws")

    def __init__(
        self,
        kind: _TransportKind,
        queue: asyncio.Queue[dict[str, Any]] | None = None,
        ws: WebSocket | None = None,
    ):
        self.kind = kind
        self.queue = queue
        self.ws = ws


_subscribers: set[_Subscriber] = set()
_lock = asyncio.Lock()

# Inbound message handlers — keyed by message "action" field
_inbound_handlers: dict[str, Any] = {}


def on_ws_message(action: str):
    """Decorator to register a handler for inbound WebSocket messages."""

    def decorator(fn):
        _inbound_handlers[action] = fn
        return fn

    return decorator


async def publish_event(event_type: str, data: dict[str, Any]) -> None:
    """Broadcast an event to every connected client (WS + SSE)."""
    payload = {
        "event": event_type,
        "data": {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    json_str = json.dumps(payload["data"])

    async with _lock:
        dead: list[_Subscriber] = []
        for sub in _subscribers:
            try:
                if sub.kind == _TransportKind.SSE:
                    assert sub.queue is not None
                    sub.queue.put_nowait(payload)
                else:
                    assert sub.ws is not None
                    await sub.ws.send_text(json_str)
            except (asyncio.QueueFull, WebSocketDisconnect, RuntimeError):
                dead.append(sub)
        for sub in dead:
            _subscribers.discard(sub)
            logger.warning("Stream: dropped slow %s consumer", sub.kind.value)


# ---------------------------------------------------------------------------
# SSE transport (fallback)
# ---------------------------------------------------------------------------


async def _sse_subscribe() -> tuple[_Subscriber, asyncio.Queue[dict[str, Any]]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
    sub = _Subscriber(kind=_TransportKind.SSE, queue=q)
    async with _lock:
        _subscribers.add(sub)
    return sub, q


async def _sse_unsubscribe(sub: _Subscriber) -> None:
    async with _lock:
        _subscribers.discard(sub)


async def _sse_event_generator():
    """Yield events from a per-client queue, with periodic heartbeats."""
    sub, q = await _sse_subscribe()
    try:
        while True:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL_SECONDS)
                yield {
                    "event": payload["event"],
                    "data": json.dumps(payload["data"]),
                }
            except asyncio.TimeoutError:
                yield {
                    "event": "heartbeat",
                    "data": json.dumps(
                        {
                            "type": "heartbeat",
                            "data": {},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                }
    finally:
        await _sse_unsubscribe(sub)


@router.get("/api/v1/stream")
async def stream_events():
    """SSE endpoint — fallback for clients that don't support WebSocket."""
    return EventSourceResponse(_sse_event_generator())


# ---------------------------------------------------------------------------
# WebSocket transport (primary)
# ---------------------------------------------------------------------------


async def _ws_subscribe(ws: WebSocket) -> _Subscriber:
    sub = _Subscriber(kind=_TransportKind.WS, ws=ws)
    async with _lock:
        _subscribers.add(sub)
    return sub


async def _ws_unsubscribe(sub: _Subscriber) -> None:
    async with _lock:
        _subscribers.discard(sub)


async def _ws_heartbeat(ws: WebSocket, stop: asyncio.Event) -> None:
    """Send periodic heartbeats to keep the WS connection alive."""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            try:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "heartbeat",
                            "data": {},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                )
            except (WebSocketDisconnect, RuntimeError):
                break


async def _handle_inbound(message: str) -> dict[str, Any] | None:
    """Route an inbound WS message to its registered handler."""
    try:
        parsed = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return {"type": "error", "data": {"message": "Invalid JSON"}}

    action = parsed.get("action")
    if not action:
        return {"type": "error", "data": {"message": "Missing 'action' field"}}

    handler = _inbound_handlers.get(action)
    if not handler:
        return {"type": "error", "data": {"message": f"Unknown action: {action}"}}

    try:
        result = await handler(parsed)
        return result
    except Exception as exc:
        logger.exception("Error handling WS action %s", action)
        return {"type": "error", "data": {"message": str(exc)}}


@router.websocket("/api/v1/ws")
async def websocket_stream(ws: WebSocket):
    """WebSocket endpoint — primary real-time transport with bidirectional messaging."""
    await ws.accept()
    sub = await _ws_subscribe(ws)
    stop = asyncio.Event()

    # Send connection confirmation
    await ws.send_text(
        json.dumps(
            {
                "type": "connected",
                "data": {"transport": "websocket", "protocol_version": 1},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    heartbeat_task = asyncio.create_task(_ws_heartbeat(ws, stop))

    try:
        while True:
            message = await ws.receive_text()
            response = await _handle_inbound(message)
            if response is not None:
                await ws.send_text(json.dumps(response))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except RuntimeError:
        logger.info("WebSocket connection closed")
    finally:
        stop.set()
        heartbeat_task.cancel()
        await _ws_unsubscribe(sub)


# ---------------------------------------------------------------------------
# Built-in inbound handlers (bidirectional features)
# ---------------------------------------------------------------------------


@on_ws_message("ping")
async def _handle_ping(_msg: dict[str, Any]) -> dict[str, Any]:
    """Respond to ping with pong — latency measurement."""
    return {
        "type": "pong",
        "data": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@on_ws_message("subscribe_filter")
async def _handle_subscribe_filter(msg: dict[str, Any]) -> dict[str, Any]:
    """Acknowledge a client's event filter preference (future: per-client filtering)."""
    event_types = msg.get("event_types", [])
    return {
        "type": "filter_ack",
        "data": {"event_types": event_types},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
