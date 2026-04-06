from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DemandSignal


async def list_demand_signals(
    db: AsyncSession,
    product_id: str | None = None,
    region: str | None = None,
    limit: int = 4000,
) -> list[DemandSignal]:
    stmt = select(DemandSignal).order_by(DemandSignal.signal_date.asc()).limit(limit)
    if product_id:
        stmt = stmt.where(DemandSignal.product_id == product_id)
    if region:
        stmt = stmt.where(DemandSignal.region == region)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_demand_summary(db: AsyncSession) -> list[dict]:
    stmt = (
        select(
            DemandSignal.product_id,
            DemandSignal.region,
            func.sum(DemandSignal.forecast_qty).label("total_forecast"),
            func.coalesce(func.sum(DemandSignal.actual_qty), 0).label("total_actual"),
            func.coalesce(func.avg(DemandSignal.variance_pct), 0.0).label("avg_variance_pct"),
        )
        .group_by(DemandSignal.product_id, DemandSignal.region)
        .order_by(DemandSignal.product_id, DemandSignal.region)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [row._asdict() for row in rows]
