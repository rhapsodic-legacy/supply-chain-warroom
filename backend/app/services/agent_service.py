from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentDecision


async def list_decisions(
    db: AsyncSession,
    agent_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[AgentDecision]:
    stmt = select(AgentDecision).order_by(AgentDecision.decided_at.desc()).limit(limit)
    if agent_type:
        stmt = stmt.where(AgentDecision.agent_type == agent_type)
    if status:
        stmt = stmt.where(AgentDecision.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_decision(db: AsyncSession, decision_id: str) -> AgentDecision | None:
    result = await db.execute(select(AgentDecision).where(AgentDecision.id == decision_id))
    return result.scalar_one_or_none()


VALID_TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"approved", "rejected"},
    "approved": {"executed", "rejected"},
}


async def update_decision_status(
    db: AsyncSession,
    decision_id: str,
    action: str,
    notes: str | None = None,
) -> AgentDecision | None:
    """Transition a decision's status (approve/reject).

    Returns the updated decision, or None if not found.
    Raises ValueError for invalid transitions.
    """
    decision = await get_decision(db, decision_id)
    if decision is None:
        return None

    target_status = "approved" if action == "approve" else "rejected"

    allowed = VALID_TRANSITIONS.get(decision.status, set())
    if target_status not in allowed:
        raise ValueError(
            f"Cannot {action} a decision with status '{decision.status}'. "
            f"Valid transitions: {allowed or 'none'}"
        )

    decision.status = target_status
    decision.outcome = target_status
    if notes:
        decision.outcome_notes = notes

    if target_status == "approved":
        decision.executed_at = datetime.utcnow()

    await db.flush()
    await db.refresh(decision)

    # Broadcast via SSE
    from app.routers.stream import publish_event

    await publish_event("agent_action", {
        "action": f"Decision {target_status}: {decision.decision_summary[:100]}",
        "agent_type": decision.agent_type,
        "decision_type": decision.decision_type,
        "decision_id": decision.id,
        "status": target_status,
    })

    return decision
