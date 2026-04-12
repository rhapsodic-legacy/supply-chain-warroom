from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ShippingRoute
from app.schemas import ShippingRouteResponse

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


@router.get("", response_model=list[ShippingRouteResponse])
async def list_routes(db: AsyncSession = Depends(get_db)):
    stmt = select(ShippingRoute).order_by(ShippingRoute.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{route_id}", response_model=ShippingRouteResponse)
async def get_route(route_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ShippingRoute).where(ShippingRoute.id == route_id)
    result = await db.execute(stmt)
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route
