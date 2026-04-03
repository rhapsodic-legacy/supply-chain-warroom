"""Scenario and disruption definitions for the Monte Carlo engine.

All structures are plain dataclasses with no I/O dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class Disruption:
    """A single disruption event within a scenario."""

    type: str  # "route_closure", "capacity_reduction", "node_shutdown", "demand_spike", "cost_increase"
    affected_ids: list[str]  # node or edge IDs
    severity: float  # 0-1
    duration_days: int
    parameters: dict = field(default_factory=dict)  # type-specific params


@dataclass
class Scenario:
    """A named collection of disruptions applied over a time horizon."""

    name: str
    description: str
    disruptions: list[Disruption]
    time_horizon_days: int = 90


# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------

def suez_canal_closure(route_ids_asia_europe: list[str] | None = None) -> Scenario:
    """21-day closure of all Asia -> Europe ocean routes (e.g. via Suez).

    If *route_ids_asia_europe* is ``None`` the disruption ``affected_ids``
    will be empty and ``engine.py`` will pattern-match by transport mode /
    origin-region at runtime.
    """
    return Scenario(
        name="Suez Canal Closure",
        description=(
            "A 21-day complete closure of the Suez Canal blocks all "
            "ocean freight transiting between Asia and Europe, forcing "
            "costly rerouting around the Cape of Good Hope."
        ),
        disruptions=[
            Disruption(
                type="route_closure",
                affected_ids=route_ids_asia_europe or [],
                severity=0.9,
                duration_days=21,
                parameters={"chokepoint": "suez", "match_transport": "ocean"},
            ),
        ],
        time_horizon_days=90,
    )


def shanghai_port_congestion(shanghai_edge_ids: list[str] | None = None) -> Scenario:
    """14-day severe congestion at Shanghai port — capacity drops to 30%."""
    return Scenario(
        name="Shanghai Port Congestion",
        description=(
            "Major congestion at Shanghai port reduces throughput to "
            "30% of normal capacity for 14 days, creating cascading "
            "delays across trans-Pacific supply chains."
        ),
        disruptions=[
            Disruption(
                type="capacity_reduction",
                affected_ids=shanghai_edge_ids or [],
                severity=0.7,
                duration_days=14,
                parameters={
                    "remaining_fraction": 0.30,
                    "match_port": "Shanghai",
                },
            ),
        ],
        time_horizon_days=90,
    )


def single_source_supplier_failure(supplier_id: str = "") -> Scenario:
    """Complete 30-day shutdown of the highest-volume East Asia supplier."""
    return Scenario(
        name="Single-Source Supplier Failure",
        description=(
            "The highest-volume East Asia supplier experiences a "
            "complete shutdown for 30 days due to a factory fire or "
            "regulatory action, eliminating all output."
        ),
        disruptions=[
            Disruption(
                type="node_shutdown",
                affected_ids=[supplier_id] if supplier_id else [],
                severity=1.0,
                duration_days=30,
                parameters={"match_region": "East Asia", "pick": "highest_capacity"},
            ),
        ],
        time_horizon_days=90,
    )


def demand_shock() -> Scenario:
    """60% demand spike across all electronics products for 45 days."""
    return Scenario(
        name="Demand Shock",
        description=(
            "A sudden 60% surge in demand for electronics products "
            "over 45 days strains inbound logistics and depletes "
            "safety stock across the network."
        ),
        disruptions=[
            Disruption(
                type="demand_spike",
                affected_ids=[],  # applies globally
                severity=0.6,
                duration_days=45,
                parameters={"demand_multiplier": 1.60, "category": "electronics"},
            ),
        ],
        time_horizon_days=90,
    )


PRESET_SCENARIOS: dict[str, Scenario] = {
    "suez_canal_closure": suez_canal_closure(),
    "shanghai_port_congestion": shanghai_port_congestion(),
    "single_source_supplier_failure": single_source_supplier_failure(),
    "demand_shock": demand_shock(),
}


# ---------------------------------------------------------------------------
# Custom scenario builder
# ---------------------------------------------------------------------------

def create_scenario_from_params(params: dict) -> Scenario:
    """Build a ``Scenario`` from a free-form API request dictionary.

    Expected shape::

        {
            "name": "My Scenario",
            "description": "...",
            "time_horizon_days": 90,        # optional, default 90
            "disruptions": [
                {
                    "type": "route_closure",
                    "affected_ids": ["id1", "id2"],
                    "severity": 0.8,
                    "duration_days": 14,
                    "parameters": {...}
                },
                ...
            ]
        }

    If ``params`` contains a ``preset`` key instead, the matching preset
    is returned (optionally with overrides applied).
    """

    # --- Preset shortcut --------------------------------------------------
    if "preset" in params:
        preset_key = params["preset"]
        if preset_key not in PRESET_SCENARIOS:
            raise ValueError(
                f"Unknown preset '{preset_key}'. "
                f"Available: {list(PRESET_SCENARIOS.keys())}"
            )
        scenario = PRESET_SCENARIOS[preset_key]
        # Allow overriding time horizon
        if "time_horizon_days" in params:
            scenario = Scenario(
                name=scenario.name,
                description=scenario.description,
                disruptions=scenario.disruptions,
                time_horizon_days=int(params["time_horizon_days"]),
            )
        return scenario

    # --- Full custom definition -------------------------------------------
    raw_disruptions = params.get("disruptions", [])
    disruptions = [
        Disruption(
            type=d["type"],
            affected_ids=d.get("affected_ids", []),
            severity=float(d.get("severity", 0.5)),
            duration_days=int(d.get("duration_days", 14)),
            parameters=d.get("parameters", {}),
        )
        for d in raw_disruptions
    ]

    return Scenario(
        name=params.get("name", "Custom Scenario"),
        description=params.get("description", ""),
        disruptions=disruptions,
        time_horizon_days=int(params.get("time_horizon_days", 90)),
    )
