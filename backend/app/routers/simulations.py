from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ExecutiveSummaryResponse,
    SimulationBrief,
    SimulationCompareRequest,
    SimulationCompareResponse,
    SimulationCreate,
    SimulationResponse,
)
from app.services import executive_summary_service, simulation_service

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])


@router.get("", response_model=list[SimulationBrief])
async def list_simulations(db: AsyncSession = Depends(get_db)):
    return await simulation_service.list_simulations(db)


@router.post("/compare", response_model=SimulationCompareResponse)
async def compare_simulations(data: SimulationCompareRequest, db: AsyncSession = Depends(get_db)):
    if len(data.simulation_ids) < 2:
        raise HTTPException(
            status_code=400, detail="At least 2 simulations required for comparison"
        )
    if len(data.simulation_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 simulations for comparison")
    sims = []
    for sid in data.simulation_ids:
        sim = await simulation_service.get_simulation(db, sid)
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation {sid} not found")
        if sim.status != "completed":
            raise HTTPException(
                status_code=400, detail=f"Simulation '{sim.name}' has not completed"
            )
        sims.append(sim)
    return SimulationCompareResponse(simulations=sims)


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation(sim_id: str, db: AsyncSession = Depends(get_db)):
    sim = await simulation_service.get_simulation(db, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.post("", response_model=SimulationResponse, status_code=201)
async def create_simulation(data: SimulationCreate, db: AsyncSession = Depends(get_db)):
    sim = await simulation_service.create_simulation(db, data)
    # Auto-run immediately so the caller gets results in one round trip
    result = await simulation_service.run_simulation(db, sim.id)
    return result or sim


@router.post("/{sim_id}/run", response_model=SimulationResponse)
async def run_simulation(sim_id: str, db: AsyncSession = Depends(get_db)):
    sim = await simulation_service.run_simulation(db, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.get("/{sim_id}/executive-summary", response_model=ExecutiveSummaryResponse)
async def get_executive_summary(sim_id: str, db: AsyncSession = Depends(get_db)):
    result = await executive_summary_service.generate_summary(db, sim_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found or not completed")
    return result
