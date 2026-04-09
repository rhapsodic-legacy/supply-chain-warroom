"""Tests for the SSE broadcast event bus."""

from __future__ import annotations

import asyncio

import pytest

from app.routers.stream import _subscribers, publish_event, _subscribe, _unsubscribe


@pytest.mark.asyncio
async def test_publish_reaches_all_subscribers():
    """Every connected subscriber should receive the published event."""
    q1 = await _subscribe()
    q2 = await _subscribe()
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
        await _unsubscribe(q1)
        await _unsubscribe(q2)


@pytest.mark.asyncio
async def test_unsubscribe_removes_consumer():
    """After unsubscribing, the queue should no longer receive events."""
    q = await _subscribe()
    await _unsubscribe(q)

    await publish_event("heartbeat", {})

    assert q.empty()


@pytest.mark.asyncio
async def test_slow_consumer_dropped():
    """A subscriber whose queue is full should be evicted, not block others."""
    q_slow = await _subscribe()
    q_fast = await _subscribe()
    try:
        # Fill up the slow consumer's queue
        for i in range(256):
            q_slow.put_nowait({"event": "filler", "data": {"i": i}})

        # Next publish should drop q_slow but still reach q_fast
        await publish_event("test", {"ok": True})

        assert not q_fast.empty()
        msg = q_fast.get_nowait()
        assert msg["data"]["data"]["ok"] is True

        # q_slow should have been evicted from subscribers
        assert q_slow not in _subscribers
    finally:
        await _unsubscribe(q_fast)
        # q_slow already removed, but safe to call again
        await _unsubscribe(q_slow)
