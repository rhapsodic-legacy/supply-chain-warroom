from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentHandoff


async def list_handoffs(
    db: AsyncSession,
    session_id: str | None = None,
    limit: int = 50,
) -> list[AgentHandoff]:
    stmt = select(AgentHandoff).order_by(AgentHandoff.started_at.desc()).limit(limit)
    if session_id:
        stmt = stmt.where(AgentHandoff.session_id == session_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_sessions(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Return recent handoff sessions grouped for pipeline display."""
    # Get recent handoffs ordered by session then sequence
    stmt = (
        select(AgentHandoff)
        .order_by(AgentHandoff.started_at.desc())
        .limit(limit * 5)  # fetch enough to cover multiple sessions
    )
    result = await db.execute(stmt)
    handoffs = list(result.scalars().all())

    # Group by session_id
    sessions: dict[str, list[AgentHandoff]] = {}
    for h in handoffs:
        sessions.setdefault(h.session_id, []).append(h)

    # Sort each session's handoffs by sequence and build response
    output = []
    for sid, items in sessions.items():
        items.sort(key=lambda x: x.sequence)
        started = min(h.started_at for h in items)
        completed_times = [h.completed_at for h in items if h.completed_at]
        completed = max(completed_times) if completed_times else None
        total_ms = sum(h.duration_ms or 0 for h in items) if completed_times else None
        output.append(
            {
                "session_id": sid,
                "handoffs": items,
                "started_at": started,
                "completed_at": completed,
                "total_duration_ms": total_ms,
            }
        )

    # Sort sessions by start time descending, cap at limit
    output.sort(key=lambda s: s["started_at"], reverse=True)
    return output[:limit]
