from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import RiskEvent
from app.schemas import RiskEventCreate


async def list_risk_events(
    db: AsyncSession,
    active_only: bool = False,
    severity: str | None = None,
) -> list[RiskEvent]:
    stmt = (
        select(RiskEvent)
        .options(selectinload(RiskEvent.impacts))
        .order_by(RiskEvent.started_at.desc())
    )
    if active_only:
        stmt = stmt.where(RiskEvent.is_active.is_(True))
    if severity:
        stmt = stmt.where(RiskEvent.severity == severity)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_risk_event(db: AsyncSession, event_id: str) -> RiskEvent | None:
    stmt = (
        select(RiskEvent).where(RiskEvent.id == event_id).options(selectinload(RiskEvent.impacts))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_risk_event(db: AsyncSession, data: RiskEventCreate) -> RiskEvent:
    event = RiskEvent(**data.model_dump())
    db.add(event)
    await db.flush()
    await db.refresh(event, attribute_names=["impacts"])

    # Push real-time update to all SSE consumers
    from app.routers.stream import publish_event

    await publish_event("risk_update", {
        "id": event.id,
        "title": event.title,
        "severity": event.severity,
        "severity_score": float(event.severity_score) if event.severity_score else None,
        "event_type": event.event_type,
        "affected_region": event.affected_region,
        "description": event.description,
    })

    return event
