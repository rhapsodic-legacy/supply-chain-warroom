"""Monte Carlo simulation engine for supply chain disruption analysis.

Pure computation -- no database calls, no LLM calls.  Receives a
``SupplyChainNetwork`` and a ``Scenario``, returns distribution statistics.

Performance target: 10 000 iterations in < 5 seconds on a modern laptop.
Achieved via NumPy vectorized sampling and batched day-level computation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.simulation.network import SupplyChainNetwork
from app.simulation.scenarios import Disruption, Scenario


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------


@dataclass
class IterationResult:
    """Metrics produced by a single Monte-Carlo iteration."""

    total_cost: float
    max_delay_days: float
    avg_fill_rate: float
    stockout_events: int


@dataclass
class DistributionStats:
    """Summary statistics over a NumPy array of scalar values."""

    mean: float
    std_dev: float
    p50: float
    p90: float
    p95: float
    p99: float
    min_val: float
    max_val: float

    @classmethod
    def from_values(cls, values: np.ndarray) -> DistributionStats:
        if values.size == 0:
            return cls(0, 0, 0, 0, 0, 0, 0, 0)
        return cls(
            mean=float(np.mean(values)),
            std_dev=float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
            p50=float(np.percentile(values, 50)),
            p90=float(np.percentile(values, 90)),
            p95=float(np.percentile(values, 95)),
            p99=float(np.percentile(values, 99)),
            min_val=float(np.min(values)),
            max_val=float(np.max(values)),
        )


@dataclass
class SimulationResult:
    """Full output of a simulation run."""

    scenario_name: str
    iterations: int
    time_horizon_days: int
    cost_distribution: DistributionStats
    delay_distribution: DistributionStats
    fill_rate_distribution: DistributionStats
    stockout_distribution: DistributionStats
    baseline_cost: float
    baseline_delay: float
    baseline_fill_rate: float


# ---------------------------------------------------------------------------
# Internal helpers — log-normal parameterisation
# ---------------------------------------------------------------------------


def _lognormal_params(mean: float, std: float) -> tuple[float, float]:
    """Convert desired (mean, std) to log-normal (mu, sigma) parameters.

    For a log-normal variable X with parameters mu, sigma:
        E[X] = exp(mu + sigma^2/2)
        Var[X] = (exp(sigma^2) - 1) * exp(2*mu + sigma^2)
    """
    if mean <= 0:
        return 0.0, 0.0
    std = max(std, 1e-6)
    variance = std**2
    sigma_sq = np.log1p(variance / (mean**2))
    mu = np.log(mean) - sigma_sq / 2
    sigma = np.sqrt(sigma_sq)
    return float(mu), float(sigma)


# ---------------------------------------------------------------------------
# Path pre-computation
# ---------------------------------------------------------------------------


@dataclass
class _PathInfo:
    """Pre-computed information about a supply path through the network."""

    edge_indices: list[int]  # indices into the edge arrays
    base_cost: float
    base_lead_time: float


def _precompute_paths(
    network: SupplyChainNetwork,
) -> tuple[
    list[str],  # edge_ids ordered
    np.ndarray,  # base_lead_times  (E,)
    np.ndarray,  # lead_time_stds   (E,)
    np.ndarray,  # costs_per_unit   (E,)
    np.ndarray,  # capacities       (E,)
    np.ndarray,  # reliabilities    (E,)
    list[_PathInfo],  # paths from suppliers to US_DEMAND
]:
    """Flatten network edges into arrays and find all supplier->customer paths."""

    edge_list = list(network.edges.values())
    edge_ids = [e.id for e in edge_list]

    base_lead_times = np.array([e.base_lead_time for e in edge_list], dtype=np.float64)
    lead_time_stds = np.array([e.lead_time_std for e in edge_list], dtype=np.float64)
    costs = np.array([e.cost_per_unit for e in edge_list], dtype=np.float64)
    capacities = np.array([e.capacity_per_day for e in edge_list], dtype=np.float64)
    reliabilities = np.array([e.reliability for e in edge_list], dtype=np.float64)

    # Build edge-id -> index map
    eid_to_idx: dict[str, int] = {eid: i for i, eid in enumerate(edge_ids)}

    # Find supplier and customer nodes
    supplier_ids = [n.id for n in network.nodes.values() if n.type == "supplier"]
    customer_ids = [n.id for n in network.nodes.values() if n.type == "customer"]

    paths: list[_PathInfo] = []
    for sid in supplier_ids:
        for cid in customer_ids:
            for edge_path in network.find_alternative_paths(sid, cid, max_depth=6):
                indices = [eid_to_idx[e.id] for e in edge_path]
                bc = sum(costs[i] for i in indices)
                blt = sum(base_lead_times[i] for i in indices)
                paths.append(_PathInfo(edge_indices=indices, base_cost=bc, base_lead_time=blt))

    return edge_ids, base_lead_times, lead_time_stds, costs, capacities, reliabilities, paths


# ---------------------------------------------------------------------------
# Disruption matching helpers
# ---------------------------------------------------------------------------


def _resolve_disruption_ids(
    disruption: Disruption,
    network: SupplyChainNetwork,
) -> list[str]:
    """Expand disruption affected_ids using pattern-matching parameters.

    When a preset scenario is created without knowing specific IDs, the
    ``parameters`` dict carries match hints (e.g. ``match_port``,
    ``match_transport``, ``match_region``, ``pick``).
    """
    if disruption.affected_ids:
        return disruption.affected_ids

    params = disruption.parameters
    matched: list[str] = []

    # Match edges by port name
    match_port = params.get("match_port")
    if match_port:
        for eid, edge in network.edges.items():
            src = network.nodes.get(edge.source_id)
            tgt = network.nodes.get(edge.target_id)
            if src and match_port.lower() in src.name.lower():
                matched.append(eid)
            elif tgt and match_port.lower() in tgt.name.lower():
                matched.append(eid)

    # Match edges by transport mode
    match_transport = params.get("match_transport")
    if match_transport and not matched:
        for eid, edge in network.edges.items():
            if edge.transport_mode == match_transport:
                matched.append(eid)

    # Match nodes by region (for node_shutdown)
    match_region = params.get("match_region")
    if match_region and not matched:
        candidates = [
            n for n in network.nodes.values() if n.region == match_region and n.type == "supplier"
        ]
        pick = params.get("pick")
        if pick == "highest_capacity" and candidates:
            candidates.sort(key=lambda n: n.capacity_per_day, reverse=True)
            matched = [candidates[0].id]
        else:
            matched = [n.id for n in candidates]

    return matched


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------


def _simulate_baseline(
    paths: list[_PathInfo],
    base_lead_times: np.ndarray,
    lead_time_stds: np.ndarray,
    costs: np.ndarray,
    capacities: np.ndarray,
    time_horizon: int,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """Run a single quick baseline pass (no disruptions) and return
    (total_cost, max_delay, avg_fill_rate).
    """
    if not paths:
        return 0.0, 0.0, 0.0

    n_paths = len(paths)
    # For baseline: use mean lead times (deterministic) with small noise
    total_cost = 0.0
    max_delay = 0.0
    total_fill = 0.0

    for p in paths:
        idx = p.edge_indices
        lt = float(np.sum(base_lead_times[idx]))
        cost = float(np.sum(costs[idx]))
        cap = float(np.min(capacities[idx]))  # bottleneck capacity
        daily_flow = min(cap, 100.0)  # normalised demand units

        days_active = max(time_horizon - lt, 0)
        total_cost += cost * daily_flow * days_active
        max_delay = max(max_delay, lt)
        # fill rate: fraction of horizon where goods are flowing
        total_fill += days_active / time_horizon if time_horizon > 0 else 1.0

    avg_fill = total_fill / n_paths if n_paths else 1.0
    return total_cost / n_paths, max_delay, min(avg_fill, 1.0)


def run_simulation(
    network: SupplyChainNetwork,
    scenario: Scenario,
    iterations: int = 10_000,
    seed: int | None = None,
) -> SimulationResult:
    """Execute a full Monte-Carlo simulation.

    Parameters
    ----------
    network:
        The supply chain graph (will not be mutated).
    scenario:
        Disruption scenario to evaluate.
    iterations:
        Number of Monte-Carlo iterations.
    seed:
        Optional RNG seed for reproducibility.

    Returns
    -------
    SimulationResult
        Distribution statistics comparing disrupted vs. baseline performance.
    """
    rng = np.random.default_rng(seed)
    time_horizon = scenario.time_horizon_days

    # --- Pre-compute paths on the clean network ---------------------------
    (
        edge_ids,
        base_lead_times,
        lead_time_stds,
        costs,
        capacities,
        reliabilities,
        paths,
    ) = _precompute_paths(network)

    n_edges = len(edge_ids)
    eid_to_idx = {eid: i for i, eid in enumerate(edge_ids)}

    if not paths:
        empty = DistributionStats(0, 0, 0, 0, 0, 0, 0, 0)
        return SimulationResult(
            scenario_name=scenario.name,
            iterations=iterations,
            time_horizon_days=time_horizon,
            cost_distribution=empty,
            delay_distribution=empty,
            fill_rate_distribution=empty,
            stockout_distribution=empty,
            baseline_cost=0,
            baseline_delay=0,
            baseline_fill_rate=0,
        )

    # --- Baseline ---------------------------------------------------------
    bl_cost, bl_delay, bl_fill = _simulate_baseline(
        paths, base_lead_times, lead_time_stds, costs, capacities, time_horizon, rng
    )

    # --- Build disrupted arrays -------------------------------------------
    # Start from baseline arrays and apply disruption effects.
    d_lead_times = base_lead_times.copy()
    d_lead_time_stds = lead_time_stds.copy()
    d_costs = costs.copy()
    d_capacities = capacities.copy()
    d_reliabilities = reliabilities.copy()

    demand_multiplier = 1.0
    disruption_days: dict[int, int] = {}  # disruption index -> duration

    for di, disruption in enumerate(scenario.disruptions):
        # Resolve affected IDs using pattern matching if needed
        affected = _resolve_disruption_ids(disruption, network)
        dur = disruption.duration_days
        sev = disruption.severity
        disruption_days[di] = dur

        if disruption.type == "demand_spike":
            demand_multiplier = disruption.parameters.get("demand_multiplier", 1.0 + sev)
            continue

        for aid in affected:
            if aid in eid_to_idx:
                idx = eid_to_idx[aid]
                if disruption.type == "route_closure":
                    d_capacities[idx] = 0.0
                    d_reliabilities[idx] = 0.0
                elif disruption.type == "capacity_reduction":
                    remaining = disruption.parameters.get("remaining_fraction", 1.0 - sev)
                    d_capacities[idx] *= remaining
                    d_lead_times[idx] /= max(remaining, 0.05)
                    d_lead_time_stds[idx] *= 2.0
                elif disruption.type == "cost_increase":
                    mult = disruption.parameters.get("cost_multiplier", 1.0 + sev)
                    d_costs[idx] *= mult
            # Node-level disruptions: zero out all edges touching the node
            elif disruption.type == "node_shutdown":
                for eid, edge_obj in network.edges.items():
                    if edge_obj.source_id == aid or edge_obj.target_id == aid:
                        if eid in eid_to_idx:
                            idx = eid_to_idx[eid]
                            d_capacities[idx] = 0.0
                            d_reliabilities[idx] = 0.0

    # --- Determine max disruption duration --------------------------------
    max_disruption_days = max((d.duration_days for d in scenario.disruptions), default=0)

    # --- Pre-compute log-normal parameters for all edges ------------------
    mus = np.zeros(n_edges, dtype=np.float64)
    sigmas = np.zeros(n_edges, dtype=np.float64)
    d_mus = np.zeros(n_edges, dtype=np.float64)
    d_sigmas = np.zeros(n_edges, dtype=np.float64)

    for i in range(n_edges):
        mus[i], sigmas[i] = _lognormal_params(
            max(base_lead_times[i], 0.1), max(lead_time_stds[i], 0.01)
        )
        d_mus[i], d_sigmas[i] = _lognormal_params(
            max(d_lead_times[i], 0.1), max(d_lead_time_stds[i], 0.01)
        )

    # --- Vectorised Monte-Carlo -------------------------------------------
    # Strategy: for each iteration we sample lead times for ALL edges at
    # once, then evaluate each path.  We split the time horizon into two
    # phases: disrupted (0..max_disruption_days) and recovered
    # (max_disruption_days..time_horizon).

    n_paths = len(paths)

    # Pre-extract path edge indices into a ragged structure for fast access
    path_edge_indices: list[np.ndarray] = [np.array(p.edge_indices, dtype=np.intp) for p in paths]

    # Allocate result arrays
    iter_costs = np.empty(iterations, dtype=np.float64)
    iter_delays = np.empty(iterations, dtype=np.float64)
    iter_fills = np.empty(iterations, dtype=np.float64)
    iter_stockouts = np.empty(iterations, dtype=np.int64)

    # Batch sample: (iterations, n_edges) for disrupted and normal phases
    # Using chunked approach to limit memory: process in blocks of 2048
    block_size = min(iterations, 2048)
    n_blocks = (iterations + block_size - 1) // block_size

    for blk in range(n_blocks):
        start = blk * block_size
        end = min(start + block_size, iterations)
        bs = end - start

        # Sample lead times: (bs, n_edges)
        # Disrupted phase
        noise_d = rng.normal(size=(bs, n_edges))
        sampled_lt_disrupted = np.exp(d_mus[np.newaxis, :] + d_sigmas[np.newaxis, :] * noise_d)

        # Normal phase
        noise_n = rng.normal(size=(bs, n_edges))
        sampled_lt_normal = np.exp(mus[np.newaxis, :] + sigmas[np.newaxis, :] * noise_n)

        # Edge-level reliability sampling: does each edge "fail" on a given
        # iteration?  A Bernoulli draw — if it fails, lead time is doubled.
        reliability_rolls = rng.uniform(size=(bs, n_edges))
        fail_mask_d = reliability_rolls > d_reliabilities[np.newaxis, :]
        fail_mask_n = reliability_rolls > reliabilities[np.newaxis, :]

        sampled_lt_disrupted = np.where(
            fail_mask_d, sampled_lt_disrupted * 2.0, sampled_lt_disrupted
        )
        sampled_lt_normal = np.where(fail_mask_n, sampled_lt_normal * 1.3, sampled_lt_normal)

        # Demand noise: Poisson-like variation around base demand
        base_demand = 100.0  # normalised daily demand units per path
        demand_normal = rng.poisson(lam=base_demand, size=bs).astype(np.float64)
        demand_disrupted = rng.poisson(lam=base_demand * demand_multiplier, size=bs).astype(
            np.float64
        )

        # Evaluate each path for this block
        block_costs = np.zeros(bs, dtype=np.float64)
        block_delays = np.zeros(bs, dtype=np.float64)
        block_fills = np.zeros(bs, dtype=np.float64)
        block_stockouts = np.zeros(bs, dtype=np.int64)

        for pi, eidx in enumerate(path_edge_indices):
            # --- Disrupted phase ------------------------------------------
            path_lt_d = sampled_lt_disrupted[:, eidx].sum(axis=1)  # (bs,)
            path_cost_d = d_costs[eidx].sum()
            path_cap_d = d_capacities[eidx].min()  # bottleneck

            # --- Normal phase ---------------------------------------------
            path_lt_n = sampled_lt_normal[:, eidx].sum(axis=1)  # (bs,)
            path_cost_n = costs[eidx].sum()
            path_cap_n = capacities[eidx].min()

            # Combine phases
            disrupted_frac = min(max_disruption_days / time_horizon, 1.0) if time_horizon > 0 else 0
            normal_frac = 1.0 - disrupted_frac

            # Weighted lead time across phases
            avg_lt = path_lt_d * disrupted_frac + path_lt_n * normal_frac

            # Daily flow: min(demand, bottleneck capacity)
            flow_d = np.minimum(demand_disrupted, path_cap_d)
            flow_n = np.minimum(demand_normal, path_cap_n)

            # Cost for this path
            cost_d = flow_d * path_cost_d * max_disruption_days
            cost_n = flow_n * path_cost_n * max(time_horizon - max_disruption_days, 0)
            path_total_cost = cost_d + cost_n

            # Fill rate: fraction of demand satisfied
            fill_d = np.where(demand_disrupted > 0, flow_d / demand_disrupted, 1.0)
            fill_n = np.where(demand_normal > 0, flow_n / demand_normal, 1.0)
            path_fill = fill_d * disrupted_frac + fill_n * normal_frac

            # Stockout: days where capacity = 0 during disrupted phase
            stockout_days = max_disruption_days if path_cap_d <= 0 else 0
            path_stockout = np.full(bs, stockout_days, dtype=np.int64)

            block_costs += path_total_cost
            block_delays = np.maximum(block_delays, avg_lt)
            block_fills += path_fill
            block_stockouts += path_stockout

        # Average fill across paths
        if n_paths > 0:
            block_fills /= n_paths
            block_costs /= n_paths  # average cost per path

        iter_costs[start:end] = block_costs
        iter_delays[start:end] = block_delays
        iter_fills[start:end] = np.clip(block_fills, 0.0, 1.0)
        iter_stockouts[start:end] = block_stockouts

    # --- Assemble results -------------------------------------------------
    return SimulationResult(
        scenario_name=scenario.name,
        iterations=iterations,
        time_horizon_days=time_horizon,
        cost_distribution=DistributionStats.from_values(iter_costs),
        delay_distribution=DistributionStats.from_values(iter_delays),
        fill_rate_distribution=DistributionStats.from_values(iter_fills),
        stockout_distribution=DistributionStats.from_values(iter_stockouts.astype(np.float64)),
        baseline_cost=bl_cost,
        baseline_delay=bl_delay,
        baseline_fill_rate=bl_fill,
    )
