"""Tool implementations for agent memory — recall past decisions and record lessons.

These tools are shared across all specialist agents, giving them the ability
to learn from past outcomes and surface "last time this happened..." context.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import memory_service


async def recall_similar_decisions(
    db: AsyncSession,
    category: str | None = None,
    affected_region: str | None = None,
    risk_type: str | None = None,
    severity: str | None = None,
    limit: int = 5,
) -> str:
    """Find past decisions and lessons that match the current situation.

    Returns memories with context about what happened before, what action
    was taken, whether it worked, and what was learned.
    """
    memories = await memory_service.find_similar_memories(
        db,
        category=category,
        affected_region=affected_region,
        risk_type=risk_type,
        severity=severity,
        limit=limit,
    )

    if not memories:
        return json.dumps({
            "memories_found": 0,
            "message": "No similar past decisions found. This appears to be a novel situation.",
        })

    results = []
    for m in memories:
        results.append({
            "memory_id": m.id,
            "agent_type": m.agent_type,
            "category": m.category,
            "affected_region": m.affected_region,
            "risk_type": m.risk_type,
            "severity": m.severity,
            "situation": m.situation,
            "action_taken": m.action_taken,
            "outcome": m.outcome,
            "lesson": m.lesson,
            "confidence_score": float(m.confidence_score),
            "cost_impact": float(m.cost_impact) if m.cost_impact else None,
            "time_impact_days": m.time_impact_days,
            "occurrence_count": m.occurrence_count,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    return json.dumps({
        "memories_found": len(results),
        "memories": results,
    }, default=str)


async def record_lesson(
    db: AsyncSession,
    agent_type: str,
    category: str,
    situation: str,
    action_taken: str,
    outcome: str,
    lesson: str,
    confidence_score: float = 0.5,
    decision_id: str | None = None,
    trigger_event_id: str | None = None,
    affected_region: str | None = None,
    severity: str | None = None,
    risk_type: str | None = None,
    cost_impact: float | None = None,
    time_impact_days: int | None = None,
) -> str:
    """Record a lesson learned from a decision outcome for future reference.

    Call this after evaluating the result of an action to build the agent's
    knowledge base over time.
    """
    memory = await memory_service.store_memory(
        db,
        agent_type=agent_type,
        category=category,
        situation=situation,
        action_taken=action_taken,
        outcome=outcome,
        lesson=lesson,
        confidence_score=confidence_score,
        decision_id=decision_id,
        trigger_event_id=trigger_event_id,
        affected_region=affected_region,
        severity=severity,
        risk_type=risk_type,
        cost_impact=cost_impact,
        time_impact_days=time_impact_days,
    )

    from app.routers.stream import publish_event

    await publish_event(
        "agent_action",
        {
            "action": f"Recorded lesson: {lesson[:100]}",
            "agent_type": agent_type,
            "decision_type": "memory_recorded",
            "memory_id": memory.id,
            "category": category,
            "outcome": outcome,
        },
    )

    return json.dumps({
        "status": "recorded",
        "memory_id": memory.id,
        "message": f"Lesson recorded for category '{category}'. "
        f"This will inform future decisions in similar situations.",
    })
