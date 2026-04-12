from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import RiskEventCreate, RiskEventResponse
from app.services import risk_service

router = APIRouter(prefix="/api/v1/risks", tags=["risks"])


@router.get("", response_model=list[RiskEventResponse])
async def list_risk_events(
    active_only: bool = Query(False),
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await risk_service.list_risk_events(db, active_only=active_only, severity=severity)


@router.get("/{event_id}", response_model=RiskEventResponse)
async def get_risk_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await risk_service.get_risk_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Risk event not found")
    return event


@router.post("", response_model=RiskEventResponse, status_code=201)
async def create_risk_event(data: RiskEventCreate, db: AsyncSession = Depends(get_db)):
    return await risk_service.create_risk_event(db, data)
