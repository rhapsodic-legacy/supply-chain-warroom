from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order


async def list_orders(
    db: AsyncSession,
    status: str | None = None,
    supplier_id: str | None = None,
    limit: int = 100,
) -> list[Order]:
    stmt = select(Order).order_by(Order.ordered_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Order.status == status)
    if supplier_id:
        stmt = stmt.where(Order.supplier_id == supplier_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_order(db: AsyncSession, order_id: str) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.supplier),
            selectinload(Order.product),
            selectinload(Order.route),
            selectinload(Order.events),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_stats(db: AsyncSession) -> dict:
    stmt = select(Order.status, func.count(Order.id)).group_by(Order.status)
    result = await db.execute(stmt)
    return {status: count for status, count in result.all()}
