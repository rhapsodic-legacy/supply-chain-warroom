import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Simulation, ShippingRoute, Supplier
from app.schemas import SimulationCreate
from app.simulation.engine import SimulationResult, run_simulation as run_engine
from app.simulation.network import build_network_from_db
from app.simulation.scenarios import PRESET_SCENARIOS, create_scenario_from_params

logger = logging.getLogger(__name__)

# Map frontend preset IDs to backend scenario keys
_PRESET_ALIAS: dict[str, str] = {
    "suez_closure": "suez_canal_closure",
    "china_lockdown": "shanghai_port_congestion",
    "demand_spike": "demand_shock",
    "supplier_failure": "single_source_supplier_failure",
    "energy_crisis": "demand_shock",  # closest available preset
}


def _format_results(result: SimulationResult) -> dict:
    """Convert engine SimulationResult into the baseline/mitigated/comparison dicts."""
    baseline = {
        "total_cost": result.baseline_cost,
        "fill_rate": result.baseline_fill_rate,
        "avg_lead_time": result.baseline_delay,
        "risk_score": round(1.0 - result.baseline_fill_rate, 3),
    }
    mitigated = {
        "total_cost": result.cost_distribution.mean,
        "fill_rate": result.fill_rate_distribution.mean,
        "avg_lead_time": result.delay_distribution.mean,
        "risk_score": round(1.0 - result.fill_rate_distribution.mean, 3),
    }
    comparison = {
        "cost_change_pct": round(
            (mitigated["total_cost"] - baseline["total_cost"])
            / max(baseline["total_cost"], 1.0)
            * 100,
            1,
        ),
        "fill_rate_change": round(mitigated["fill_rate"] - baseline["fill_rate"], 4),
        "delay_change_days": round(mitigated["avg_lead_time"] - baseline["avg_lead_time"], 1),
        "iterations": result.iterations,
        "time_horizon_days": result.time_horizon_days,
        "cost_p95": result.cost_distribution.p95,
        "delay_p95": result.delay_distribution.p95,
        "stockout_mean": result.stockout_distribution.mean,
    }
    return {"baseline": baseline, "mitigated": mitigated, "comparison": comparison}


async def list_simulations(db: AsyncSession) -> list[Simulation]:
    result = await db.execute(select(Simulation).order_by(Simulation.created_at.desc()))
    return list(result.scalars().all())


async def get_simulation(db: AsyncSession, sim_id: str) -> Simulation | None:
    result = await db.execute(select(Simulation).where(Simulation.id == sim_id))
    return result.scalar_one_or_none()


async def create_simulation(db: AsyncSession, data: SimulationCreate) -> Simulation:
    sim = Simulation(
        name=data.name,
        description=data.description,
        scenario_params=json.dumps(data.scenario_params),
        iterations=data.iterations,
    )
    db.add(sim)
    await db.flush()
    await db.refresh(sim)
    return sim


async def _load_network(db: AsyncSession):
    """Load suppliers and routes from DB and build a SupplyChainNetwork."""
    suppliers = list((await db.execute(select(Supplier))).scalars().all())
    routes = list((await db.execute(select(ShippingRoute))).scalars().all())
    return build_network_from_db(suppliers, routes)


def _resolve_scenario(params: dict):
    """Build a Scenario from request params, resolving frontend preset aliases."""
    scenario_key = params.get("scenario") or params.get("preset")
    if scenario_key:
        # Resolve frontend alias to backend key
        backend_key = _PRESET_ALIAS.get(scenario_key, scenario_key)
        if backend_key in PRESET_SCENARIOS:
            return PRESET_SCENARIOS[backend_key]
        # Try as a direct preset key
        return create_scenario_from_params({"preset": backend_key, **params})
    return create_scenario_from_params(params)


async def run_simulation(db: AsyncSession, sim_id: str) -> Simulation | None:
    """Run a simulation — builds network from DB, executes Monte Carlo engine."""
    sim = await get_simulation(db, sim_id)
    if sim is None:
        return None

    sim.status = "running"
    sim.started_at = datetime.utcnow()
    await db.flush()

    try:
        params = json.loads(sim.scenario_params) if sim.scenario_params else {}
        network = await _load_network(db)
        scenario = _resolve_scenario(params)

        # Run CPU-bound simulation in a thread pool
        result: SimulationResult = await asyncio.to_thread(
            run_engine, network, scenario, sim.iterations or 10_000
        )

        formatted = _format_results(result)
        sim.baseline_metrics = json.dumps(formatted["baseline"])
        sim.mitigated_metrics = json.dumps(formatted["mitigated"])
        sim.comparison = json.dumps(formatted["comparison"])
        sim.status = "completed"
    except Exception:
        logger.exception("Simulation %s failed", sim_id)
        sim.baseline_metrics = json.dumps({"error": "simulation failed"})
        sim.mitigated_metrics = json.dumps({"error": "simulation failed"})
        sim.comparison = json.dumps({"error": "simulation failed"})
        sim.status = "failed"

    sim.completed_at = datetime.utcnow()
    await db.flush()
    await db.refresh(sim)
    return sim
