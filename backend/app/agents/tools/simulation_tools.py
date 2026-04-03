"""Tool implementations for the Simulation agent.

Wraps the Monte Carlo engine and network builder, persisting results
to the simulations table.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ShippingRoute, Simulation, Supplier
from app.simulation.engine import SimulationResult, run_simulation
from app.simulation.network import SupplyChainNetwork, build_network_from_db
from app.simulation.scenarios import (
    PRESET_SCENARIOS,
    create_scenario_from_params,
)


async def list_preset_scenarios() -> str:
    """Return the catalogue of available preset disruption scenarios."""
    presets = []
    for key, scenario in PRESET_SCENARIOS.items():
        presets.append(
            {
                "key": key,
                "name": scenario.name,
                "description": scenario.description,
                "time_horizon_days": scenario.time_horizon_days,
                "disruption_count": len(scenario.disruptions),
                "disruption_types": [d.type for d in scenario.disruptions],
            }
        )
    return json.dumps(presets)


async def run_monte_carlo(
    db: AsyncSession,
    scenario_name: str | None = None,
    scenario_params: dict | None = None,
    iterations: int = 10_000,
) -> str:
    """Build the supply chain network from DB, run a Monte Carlo simulation,
    persist results, and return a summary.

    Either *scenario_name* (a preset key) or *scenario_params* (a custom
    definition dict) must be provided.
    """
    # Resolve scenario
    if scenario_name and scenario_name in PRESET_SCENARIOS:
        scenario = PRESET_SCENARIOS[scenario_name]
    elif scenario_params:
        scenario = create_scenario_from_params(scenario_params)
    elif scenario_name:
        # Treat as preset key
        scenario = create_scenario_from_params({"preset": scenario_name})
    else:
        return json.dumps({"error": "Provide either scenario_name or scenario_params."})

    # Build network from current DB state
    suppliers_result = await db.execute(
        select(Supplier).where(Supplier.is_active.is_(True))
    )
    suppliers = list(suppliers_result.scalars().all())

    routes_result = await db.execute(
        select(ShippingRoute).where(ShippingRoute.is_active.is_(True))
    )
    routes = list(routes_result.scalars().all())

    network = build_network_from_db(suppliers, routes)

    # Run simulation
    sim_result: SimulationResult = run_simulation(
        network, scenario, iterations=iterations
    )

    # Persist to DB
    def _stats_dict(stats) -> dict:
        return {
            "mean": round(stats.mean, 2),
            "std_dev": round(stats.std_dev, 2),
            "p50": round(stats.p50, 2),
            "p90": round(stats.p90, 2),
            "p95": round(stats.p95, 2),
            "p99": round(stats.p99, 2),
            "min": round(stats.min_val, 2),
            "max": round(stats.max_val, 2),
        }

    baseline_metrics = {
        "cost": round(sim_result.baseline_cost, 2),
        "delay_days": round(sim_result.baseline_delay, 2),
        "fill_rate": round(sim_result.baseline_fill_rate, 4),
    }
    mitigated_metrics = {
        "cost": _stats_dict(sim_result.cost_distribution),
        "delay_days": _stats_dict(sim_result.delay_distribution),
        "fill_rate": _stats_dict(sim_result.fill_rate_distribution),
        "stockout_events": _stats_dict(sim_result.stockout_distribution),
    }
    comparison = {
        "cost_increase_pct": round(
            (sim_result.cost_distribution.mean - sim_result.baseline_cost)
            / max(sim_result.baseline_cost, 1)
            * 100,
            2,
        ),
        "delay_increase_days": round(
            sim_result.delay_distribution.mean - sim_result.baseline_delay, 2
        ),
        "fill_rate_change": round(
            sim_result.fill_rate_distribution.mean - sim_result.baseline_fill_rate, 4
        ),
    }

    sim_record = Simulation(
        id=str(uuid.uuid4()),
        name=scenario.name,
        description=scenario.description,
        scenario_params=json.dumps(
            {"preset": scenario_name} if scenario_name else (scenario_params or {})
        ),
        status="completed",
        iterations=iterations,
        baseline_metrics=json.dumps(baseline_metrics),
        mitigated_metrics=json.dumps(mitigated_metrics),
        comparison=json.dumps(comparison),
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(sim_record)
    await db.commit()

    summary = {
        "simulation_id": sim_record.id,
        "scenario": scenario.name,
        "iterations": iterations,
        "time_horizon_days": scenario.time_horizon_days,
        "baseline": baseline_metrics,
        "disrupted": {
            "cost_mean": sim_result.cost_distribution.mean,
            "cost_p95": sim_result.cost_distribution.p95,
            "delay_mean": sim_result.delay_distribution.mean,
            "delay_p95": sim_result.delay_distribution.p95,
            "fill_rate_mean": sim_result.fill_rate_distribution.mean,
            "fill_rate_p5": sim_result.fill_rate_distribution.p50,
            "stockout_mean": sim_result.stockout_distribution.mean,
        },
        "comparison": comparison,
    }
    return json.dumps(summary, default=str)


async def query_network_stats(db: AsyncSession) -> str:
    """Return a high-level summary of the supply chain network graph."""
    suppliers_result = await db.execute(
        select(Supplier).where(Supplier.is_active.is_(True))
    )
    suppliers = list(suppliers_result.scalars().all())

    routes_result = await db.execute(
        select(ShippingRoute).where(ShippingRoute.is_active.is_(True))
    )
    routes = list(routes_result.scalars().all())

    network = build_network_from_db(suppliers, routes)

    # Compute stats
    supplier_nodes = [n for n in network.nodes.values() if n.type == "supplier"]
    port_nodes = [n for n in network.nodes.values() if n.type == "port"]
    customer_nodes = [n for n in network.nodes.values() if n.type == "customer"]

    reliabilities = [e.reliability for e in network.edges.values()]
    avg_reliability = sum(reliabilities) / len(reliabilities) if reliabilities else 0

    # Count unique transport modes
    transport_modes = set(e.transport_mode for e in network.edges.values())

    # Count routes by mode
    mode_counts: dict[str, int] = {}
    for e in network.edges.values():
        mode_counts[e.transport_mode] = mode_counts.get(e.transport_mode, 0) + 1

    stats = {
        "total_nodes": len(network.nodes),
        "supplier_nodes": len(supplier_nodes),
        "port_nodes": len(port_nodes),
        "customer_nodes": len(customer_nodes),
        "total_edges": len(network.edges),
        "avg_reliability": round(avg_reliability, 4),
        "transport_modes": list(transport_modes),
        "edges_by_mode": mode_counts,
        "regions": list(set(n.region for n in supplier_nodes)),
    }
    return json.dumps(stats, default=str)
