"""Tests for the agent memory / learning feature."""

import json
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentMemory
from app.services import memory_service


# ---------------------------------------------------------------------------
# Memory service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_memory(db_session: AsyncSession):
    """store_memory persists a memory record and returns it."""
    memory = await memory_service.store_memory(
        db_session,
        agent_type="strategy",
        category="port_closure",
        situation="Shanghai port closed due to typhoon",
        action_taken="Rerouted via Ho Chi Minh City",
        outcome="effective",
        lesson="HCMC is a viable diversion for Shanghai-bound cargo",
        confidence_score=0.85,
        affected_region="East Asia",
        severity="critical",
        risk_type="weather",
        cost_impact=18000.0,
        time_impact_days=-12,
    )

    assert memory.id is not None
    assert memory.agent_type == "strategy"
    assert memory.category == "port_closure"
    assert memory.outcome == "effective"
    assert float(memory.confidence_score) == 0.85
    assert memory.affected_region == "East Asia"


@pytest.mark.asyncio
async def test_find_similar_memories_by_category(db_session: AsyncSession):
    """find_similar_memories returns matches by category."""
    # Create two memories — one matching, one not
    await memory_service.store_memory(
        db_session,
        agent_type="strategy",
        category="port_closure",
        situation="Rotterdam strike",
        action_taken="Diverted to Hamburg",
        outcome="effective",
        lesson="Hamburg is better than Antwerp for Rotterdam diversions",
        affected_region="Europe",
    )
    await memory_service.store_memory(
        db_session,
        agent_type="strategy",
        category="demand_spike",
        situation="Automotive sensor surge",
        action_taken="Expedited orders",
        outcome="partially_effective",
        lesson="Capacity reservation agreements are cost-effective",
    )

    results = await memory_service.find_similar_memories(
        db_session,
        category="port_closure",
    )

    assert len(results) >= 1
    assert all(m.category == "port_closure" for m in results)


@pytest.mark.asyncio
async def test_find_similar_memories_by_region(db_session: AsyncSession):
    """find_similar_memories filters by region."""
    await memory_service.store_memory(
        db_session,
        agent_type="risk_monitor",
        category="weather_disruption",
        situation="Typhoon in East Asia",
        action_taken="Activated safety stock",
        outcome="effective",
        lesson="Safety stock is essential for weather events",
        affected_region="East Asia",
    )

    results = await memory_service.find_similar_memories(
        db_session,
        affected_region="East Asia",
    )

    assert len(results) >= 1
    assert any(m.affected_region == "East Asia" for m in results)


@pytest.mark.asyncio
async def test_find_similar_memories_updates_last_referenced(db_session: AsyncSession):
    """Retrieving memories updates their last_referenced_at timestamp."""
    memory = await memory_service.store_memory(
        db_session,
        agent_type="strategy",
        category="supplier_failure",
        situation="Factory fire in Shenzhen",
        action_taken="Qualified backup supplier",
        outcome="effective",
        lesson="Multi-source qualification should be proactive",
    )
    assert memory.last_referenced_at is None

    await memory_service.find_similar_memories(
        db_session,
        category="supplier_failure",
    )

    # Refresh from DB
    await db_session.refresh(memory)
    assert memory.last_referenced_at is not None


@pytest.mark.asyncio
async def test_find_similar_no_filters_returns_recent(db_session: AsyncSession):
    """With no filters, returns most recent memories."""
    await memory_service.store_memory(
        db_session,
        agent_type="strategy",
        category="logistics_bottleneck",
        situation="Port congestion",
        action_taken="Diverted containers",
        outcome="effective",
        lesson="Pacific NW ports are good overflow options",
    )

    results = await memory_service.find_similar_memories(db_session)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_list_memories_filters(db_session: AsyncSession):
    """list_memories applies optional filters."""
    await memory_service.store_memory(
        db_session,
        agent_type="execution",
        category="logistics_bottleneck",
        situation="LA port queue",
        action_taken="Diverted to Oakland",
        outcome="effective",
        lesson="Oakland is a reliable overflow option",
    )

    results = await memory_service.list_memories(db_session, agent_type="execution")
    assert all(m.agent_type == "execution" for m in results)


@pytest.mark.asyncio
async def test_get_memory(db_session: AsyncSession):
    """get_memory returns a specific memory by ID."""
    memory = await memory_service.store_memory(
        db_session,
        agent_type="strategy",
        category="geopolitical",
        situation="Taiwan Strait tensions",
        action_taken="Pre-positioned inventory in Vietnam",
        outcome="effective",
        lesson="Geographic diversification is essential",
    )

    fetched = await memory_service.get_memory(db_session, memory.id)
    assert fetched is not None
    assert fetched.id == memory.id
    assert fetched.lesson == "Geographic diversification is essential"


@pytest.mark.asyncio
async def test_get_memory_not_found(db_session: AsyncSession):
    """get_memory returns None for nonexistent ID."""
    result = await memory_service.get_memory(db_session, str(uuid.uuid4()))
    assert result is None


@pytest.mark.asyncio
async def test_increment_occurrence(db_session: AsyncSession):
    """increment_occurrence bumps the counter."""
    memory = await memory_service.store_memory(
        db_session,
        agent_type="strategy",
        category="port_closure",
        situation="Test",
        action_taken="Test action",
        outcome="effective",
        lesson="Test lesson",
    )
    assert memory.occurrence_count == 1

    await memory_service.increment_occurrence(db_session, memory.id)
    await db_session.refresh(memory)
    assert memory.occurrence_count == 2


@pytest.mark.asyncio
async def test_get_memory_stats(db_session: AsyncSession):
    """get_memory_stats returns aggregated statistics."""
    stats = await memory_service.get_memory_stats(db_session)
    assert "total_memories" in stats
    assert "by_outcome" in stats
    assert "by_category" in stats
    assert "by_agent" in stats


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_memories_endpoint(seeded_client):
    """GET /api/v1/agents/memories returns a list."""
    resp = await seeded_client.get("/api/v1/agents/memories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check schema
    first = data[0]
    assert "id" in first
    assert "agent_type" in first
    assert "category" in first
    assert "lesson" in first
    assert "outcome" in first


@pytest.mark.asyncio
async def test_list_memories_filter_by_category(seeded_client):
    """GET /api/v1/agents/memories?category=port_closure filters correctly."""
    resp = await seeded_client.get("/api/v1/agents/memories?category=port_closure")
    assert resp.status_code == 200
    data = resp.json()
    assert all(m["category"] == "port_closure" for m in data)


@pytest.mark.asyncio
async def test_memory_stats_endpoint(seeded_client):
    """GET /api/v1/agents/memories/stats returns aggregated data."""
    resp = await seeded_client.get("/api/v1/agents/memories/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_memories"] > 0
    assert isinstance(data["by_outcome"], dict)
    assert isinstance(data["by_category"], dict)


@pytest.mark.asyncio
async def test_get_memory_endpoint(seeded_client):
    """GET /api/v1/agents/memories/:id returns full detail."""
    # Get a memory ID first
    list_resp = await seeded_client.get("/api/v1/agents/memories?limit=1")
    memories = list_resp.json()
    assert len(memories) > 0

    memory_id = memories[0]["id"]
    resp = await seeded_client.get(f"/api/v1/agents/memories/{memory_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == memory_id
    assert "situation" in data
    assert "action_taken" in data
    assert "lesson" in data


@pytest.mark.asyncio
async def test_get_memory_not_found_endpoint(seeded_client):
    """GET /api/v1/agents/memories/:id returns 404 for missing ID."""
    resp = await seeded_client.get(f"/api/v1/agents/memories/{uuid.uuid4()}")
    assert resp.status_code == 404
