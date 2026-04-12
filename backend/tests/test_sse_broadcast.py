"""Tests for the unified broadcast event bus (SSE + WebSocket)."""

from __future__ import annotations

import pytest

from app.routers.stream import (
    _TransportKind,
    _lock,
    _sse_subscribe,
    _sse_unsubscribe,
    _subscribers,
    publish_event,
)


@pytest.mark.asyncio
async def test_publish_reaches_all_subscribers():
    """Every connected subscriber should receive the published event."""
    sub1, q1 = await _sse_subscribe()
    sub2, q2 = await _sse_subscribe()
    try:
        await publish_event("risk_update", {"title": "Test Event", "severity": "high"})

        msg1 = q1.get_nowait()
        msg2 = q2.get_nowait()

        assert msg1["event"] == "risk_update"
        assert msg1["data"]["type"] == "risk_update"
        assert msg1["data"]["data"]["title"] == "Test Event"
        assert "timestamp" in msg1["data"]

        assert msg2["event"] == "risk_update"
        assert msg2["data"]["data"]["severity"] == "high"
    finally:
        await _sse_unsubscribe(sub1)
        await _sse_unsubscribe(sub2)


@pytest.mark.asyncio
async def test_unsubscribe_removes_consumer():
    """After unsubscribing, the queue should no longer receive events."""
    sub, q = await _sse_subscribe()
    await _sse_unsubscribe(sub)

    await publish_event("heartbeat", {})

    assert q.empty()


@pytest.mark.asyncio
async def test_slow_consumer_dropped():
    """A subscriber whose queue is full should be evicted, not block others."""
    sub_slow, q_slow = await _sse_subscribe()
    sub_fast, q_fast = await _sse_subscribe()
    try:
        # Fill up the slow consumer's queue
        for i in range(256):
            q_slow.put_nowait({"event": "filler", "data": {"i": i}})

        # Next publish should drop sub_slow but still reach sub_fast
        await publish_event("test", {"ok": True})

        assert not q_fast.empty()
        msg = q_fast.get_nowait()
        assert msg["data"]["data"]["ok"] is True

        # sub_slow should have been evicted from subscribers
        assert sub_slow not in _subscribers
    finally:
        await _sse_unsubscribe(sub_fast)
        # sub_slow already removed, but safe to call again
        await _sse_unsubscribe(sub_slow)


@pytest.mark.asyncio
async def test_subscriber_types_tracked():
    """Both SSE and WS subscriber types are tracked in the shared set."""
    sub_sse, _ = await _sse_subscribe()
    try:
        assert sub_sse.kind == _TransportKind.SSE
        assert sub_sse in _subscribers
    finally:
        await _sse_unsubscribe(sub_sse)


@pytest.mark.asyncio
async def test_publish_to_empty_hub():
    """Publishing with no subscribers should not raise."""
    # Ensure clean state
    async with _lock:
        _subscribers.clear()
    await publish_event("test", {"data": "no-one-listening"})
    # No error means success
