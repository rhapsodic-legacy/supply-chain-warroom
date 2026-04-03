from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, RiskEvent, Supplier
from app.services.supplier_service import get_supply_health as _get_supply_health


async def get_overview(db: AsyncSession) -> dict:
    """Aggregate metrics across all tables for the dashboard."""
    total_orders_q = await db.execute(select(func.count(Order.id)))
    total_orders = total_orders_q.scalar() or 0

    active_orders_q = await db.execute(
        select(func.count(Order.id)).where(Order.status.in_(["pending", "in_transit"]))
    )
    active_orders = active_orders_q.scalar() or 0

    total_suppliers_q = await db.execute(select(func.count(Supplier.id)))
    total_suppliers = total_suppliers_q.scalar() or 0

    active_suppliers_q = await db.execute(
        select(func.count(Supplier.id)).where(Supplier.is_active.is_(True))
    )
    active_suppliers = active_suppliers_q.scalar() or 0

    active_risks_q = await db.execute(
        select(func.count(RiskEvent.id)).where(RiskEvent.is_active.is_(True))
    )
    active_risk_events = active_risks_q.scalar() or 0

    critical_risks_q = await db.execute(
        select(func.count(RiskEvent.id)).where(
            RiskEvent.is_active.is_(True),
            RiskEvent.severity == "critical",
        )
    )
    critical_risk_events = critical_risks_q.scalar() or 0

    delivered_q = await db.execute(
        select(func.count(Order.id)).where(Order.status == "delivered")
    )
    delivered = delivered_q.scalar() or 0
    avg_fill_rate = (delivered / total_orders * 100) if total_orders > 0 else 0.0

    revenue_q = await db.execute(select(func.sum(Order.total_cost)))
    total_revenue = revenue_q.scalar() or 0.0

    return {
        "total_orders": total_orders,
        "active_orders": active_orders,
        "total_suppliers": total_suppliers,
        "active_suppliers": active_suppliers,
        "active_risk_events": active_risk_events,
        "critical_risk_events": critical_risk_events,
        "avg_fill_rate": round(float(avg_fill_rate), 2),
        "total_revenue": float(total_revenue),
    }


async def get_supply_health(db: AsyncSession) -> list[dict]:
    return await _get_supply_health(db)
