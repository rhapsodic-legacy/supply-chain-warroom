from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SimulationBrief, SimulationCreate, SimulationResponse
from app.services import simulation_service

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])


@router.get("/", response_model=list[SimulationBrief])
async def list_simulations(db: AsyncSession = Depends(get_db)):
    return await simulation_service.list_simulations(db)


@router.get("/{sim_id}", response_model=SimulationResponse)
async def get_simulation(sim_id: str, db: AsyncSession = Depends(get_db)):
    sim = await simulation_service.get_simulation(db, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.post("/", response_model=SimulationResponse, status_code=201)
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
