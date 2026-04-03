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
