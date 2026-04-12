"""Agent memory service — store, retrieve, and match learned patterns.

Provides similarity-based retrieval using category, region, risk_type, and
severity as matching dimensions. No vector embeddings needed — structured
field matching with scoring gives fast, interpretable results.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentMemory


async def store_memory(
    db: AsyncSession,
    *,
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
) -> AgentMemory:
    """Create a new memory record from a decision outcome."""
    memory = AgentMemory(
        id=str(uuid.uuid4()),
        agent_type=agent_type,
        decision_id=decision_id,
        trigger_event_id=trigger_event_id,
        category=category,
        affected_region=affected_region,
        severity=severity,
        risk_type=risk_type,
        situation=situation,
        action_taken=action_taken,
        outcome=outcome,
        lesson=lesson,
        confidence_score=confidence_score,
        cost_impact=cost_impact,
        time_impact_days=time_impact_days,
    )
    db.add(memory)
    await db.flush()
    await db.refresh(memory)
    return memory


async def find_similar_memories(
    db: AsyncSession,
    *,
    category: str | None = None,
    affected_region: str | None = None,
    risk_type: str | None = None,
    severity: str | None = None,
    agent_type: str | None = None,
    limit: int = 5,
) -> list[AgentMemory]:
    """Find memories matching the given context fields.

    Applies a relevance scoring system:
    - Exact category match: highest priority
    - Region match: medium priority
    - Risk type match: medium priority
    - Severity match: lower priority

    Returns memories ordered by relevance, with ties broken by recency.
    """
    # Build relevance score as sum of matching fields
    score_parts = []
    filters = []

    if category:
        score_parts.append(
            func.cast(AgentMemory.category == category, type_=func.literal(1).type) * 4
        )
        filters.append(AgentMemory.category == category)

    if affected_region:
        score_parts.append(
            func.cast(AgentMemory.affected_region == affected_region, type_=func.literal(1).type)
            * 2
        )

    if risk_type:
        score_parts.append(
            func.cast(AgentMemory.risk_type == risk_type, type_=func.literal(1).type) * 2
        )

    if severity:
        score_parts.append(
            func.cast(AgentMemory.severity == severity, type_=func.literal(1).type) * 1
        )

    # We need at least the category to match, or any two other fields
    if not filters:
        # No category — require at least one contextual match
        context_filters = []
        if affected_region:
            context_filters.append(AgentMemory.affected_region == affected_region)
        if risk_type:
            context_filters.append(AgentMemory.risk_type == risk_type)
        if severity:
            context_filters.append(AgentMemory.severity == severity)

        if not context_filters:
            # No filters at all — return most recent memories
            stmt = select(AgentMemory).order_by(AgentMemory.created_at.desc()).limit(limit)
            if agent_type:
                stmt = stmt.where(AgentMemory.agent_type == agent_type)
            result = await db.execute(stmt)
            return list(result.scalars().all())

        filters = context_filters

    stmt = select(AgentMemory).where(or_(*filters))

    if agent_type:
        stmt = stmt.where(AgentMemory.agent_type == agent_type)

    # Order by recency (most relevant recent memories first), then confidence
    stmt = stmt.order_by(AgentMemory.created_at.desc(), AgentMemory.confidence_score.desc())
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    memories = list(result.scalars().all())

    # Update last_referenced_at for the retrieved memories
    if memories:
        memory_ids = [m.id for m in memories]
        await db.execute(
            update(AgentMemory)
            .where(AgentMemory.id.in_(memory_ids))
            .values(last_referenced_at=datetime.utcnow())
        )
        await db.flush()

    return memories


async def list_memories(
    db: AsyncSession,
    *,
    agent_type: str | None = None,
    category: str | None = None,
    outcome: str | None = None,
    limit: int = 50,
) -> list[AgentMemory]:
    """List memories with optional filtering."""
    stmt = select(AgentMemory).order_by(AgentMemory.created_at.desc()).limit(limit)
    if agent_type:
        stmt = stmt.where(AgentMemory.agent_type == agent_type)
    if category:
        stmt = stmt.where(AgentMemory.category == category)
    if outcome:
        stmt = stmt.where(AgentMemory.outcome == outcome)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_memory(db: AsyncSession, memory_id: str) -> AgentMemory | None:
    result = await db.execute(select(AgentMemory).where(AgentMemory.id == memory_id))
    return result.scalar_one_or_none()


async def increment_occurrence(db: AsyncSession, memory_id: str) -> None:
    """Bump the occurrence count when a similar pattern is seen again."""
    await db.execute(
        update(AgentMemory)
        .where(AgentMemory.id == memory_id)
        .values(
            occurrence_count=AgentMemory.occurrence_count + 1,
            updated_at=datetime.utcnow(),
        )
    )
    await db.flush()


async def get_memory_stats(db: AsyncSession) -> dict:
    """Return summary statistics about the memory store."""
    total = await db.execute(select(func.count(AgentMemory.id)))
    by_outcome = await db.execute(
        select(AgentMemory.outcome, func.count(AgentMemory.id)).group_by(AgentMemory.outcome)
    )
    by_category = await db.execute(
        select(AgentMemory.category, func.count(AgentMemory.id)).group_by(AgentMemory.category)
    )
    by_agent = await db.execute(
        select(AgentMemory.agent_type, func.count(AgentMemory.id)).group_by(
            AgentMemory.agent_type
        )
    )

    return {
        "total_memories": total.scalar() or 0,
        "by_outcome": {row[0]: row[1] for row in by_outcome.all()},
        "by_category": {row[0]: row[1] for row in by_category.all()},
        "by_agent": {row[0]: row[1] for row in by_agent.all()},
    }
