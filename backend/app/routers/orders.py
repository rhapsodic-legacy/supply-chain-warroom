from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import OrderBrief, OrderResponse
from app.services import order_service

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.get("", response_model=list[OrderBrief])
async def list_orders(
    status: str | None = Query(None),
    supplier_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.list_orders(db, status=status, supplier_id=supplier_id, limit=limit)


@router.get("/stats")
async def get_order_stats(db: AsyncSession = Depends(get_db)):
    return await order_service.get_order_stats(db)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
