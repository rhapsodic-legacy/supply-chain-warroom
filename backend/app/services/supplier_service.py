from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, RiskEvent, RiskEventImpact, Supplier


async def list_suppliers(db: AsyncSession) -> list[Supplier]:
    result = await db.execute(select(Supplier).order_by(Supplier.name))
    return list(result.scalars().all())


async def get_supplier(db: AsyncSession, supplier_id: str) -> Supplier | None:
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    return result.scalar_one_or_none()


async def get_supply_health(db: AsyncSession) -> list[dict]:
    """Join suppliers with active risk counts and pending order counts."""
    risk_sub = (
        select(
            RiskEventImpact.entity_id.label("supplier_id"),
            func.count(RiskEventImpact.id).label("active_risk_count"),
        )
        .join(RiskEvent, RiskEvent.id == RiskEventImpact.risk_event_id)
        .where(RiskEventImpact.entity_type == "supplier")
        .where(RiskEvent.is_active.is_(True))
        .group_by(RiskEventImpact.entity_id)
        .subquery()
    )

    order_sub = (
        select(
            Order.supplier_id,
            func.count(Order.id).label("pending_orders"),
        )
        .where(Order.status.in_(["pending", "in_transit"]))
        .group_by(Order.supplier_id)
        .subquery()
    )

    stmt = (
        select(
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
            Supplier.region,
            Supplier.reliability_score,
            func.coalesce(risk_sub.c.active_risk_count, 0).label("active_risk_count"),
            func.coalesce(order_sub.c.pending_orders, 0).label("pending_orders"),
        )
        .outerjoin(risk_sub, Supplier.id == risk_sub.c.supplier_id)
        .outerjoin(order_sub, Supplier.id == order_sub.c.supplier_id)
        .where(Supplier.is_active.is_(True))
        .order_by(Supplier.name)
    )

    result = await db.execute(stmt)
    rows = result.all()
    return [row._asdict() for row in rows]
