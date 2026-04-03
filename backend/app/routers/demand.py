from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DemandSignalResponse, DemandSummary
from app.services import demand_service

router = APIRouter(prefix="/api/v1/demand", tags=["demand"])


@router.get("/", response_model=list[DemandSignalResponse])
async def list_demand_signals(
    product_id: str | None = Query(None),
    region: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await demand_service.list_demand_signals(db, product_id=product_id, region=region, limit=limit)


@router.get("/summary", response_model=list[DemandSummary])
async def get_demand_summary(db: AsyncSession = Depends(get_db)):
    return await demand_service.get_demand_summary(db)
