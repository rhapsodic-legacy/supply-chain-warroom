from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DashboardOverview, SupplyHealthItem
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardOverview)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_overview(db)


@router.get("/supply-health", response_model=list[SupplyHealthItem])
async def get_supply_health(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_supply_health(db)
