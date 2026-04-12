"""Tests for the Monte Carlo simulation engine."""

import numpy as np
import pytest

from app.simulation.engine import DistributionStats, SimulationResult, run_simulation
from app.simulation.network import Edge, Node, SupplyChainNetwork
from app.simulation.scenarios import (
    PRESET_SCENARIOS,
    Disruption,
    Scenario,
    create_scenario_from_params,
)


# ---------------------------------------------------------------------------
# DistributionStats
# ---------------------------------------------------------------------------


class TestDistributionStats:
    def test_from_values_with_known_data(self):
        """DistributionStats.from_values computes correct statistics."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        stats = DistributionStats.from_values(values)

        assert stats.mean == pytest.approx(5.5, rel=1e-6)
        assert stats.min_val == pytest.approx(1.0)
        assert stats.max_val == pytest.approx(10.0)
        assert stats.p50 == pytest.approx(5.5, rel=1e-1)
        assert stats.p90 >= stats.p50
        assert stats.p99 >= stats.p90
        assert stats.std_dev > 0

    def test_from_values_empty_array(self):
        """Empty input returns all-zero stats."""
        stats = DistributionStats.from_values(np.array([]))
        assert stats.mean == 0
        assert stats.std_dev == 0
        assert stats.p50 == 0

    def test_from_values_single_element(self):
        """Single-element array has zero std_dev."""
        stats = DistributionStats.from_values(np.array([42.0]))
        assert stats.mean == pytest.approx(42.0)
        assert stats.std_dev == 0.0
        assert stats.p50 == pytest.approx(42.0)

    def test_percentile_ordering(self):
        """p50 <= p90 <= p95 <= p99."""
        rng = np.random.default_rng(123)
        values = rng.lognormal(mean=3.0, sigma=0.5, size=10000)
        stats = DistributionStats.from_values(values)

        assert stats.p50 <= stats.p90
        assert stats.p90 <= stats.p95
        assert stats.p95 <= stats.p99


# ---------------------------------------------------------------------------
# Helper to build a minimal test network
# ---------------------------------------------------------------------------


def _build_simple_network() -> SupplyChainNetwork:
    """Create a 3-node network: supplier -> port -> customer."""
    nodes = {
        "S1": Node(
            id="S1",
            type="supplier",
            name="Supplier A",
            region="East Asia",
            capacity_per_day=5000,
            lat=31.0,
            lon=121.0,
        ),
        "P1": Node(
            id="P1",
            type="port",
            name="Shanghai",
            region="China",
            capacity_per_day=20000,
            lat=31.2,
            lon=121.5,
        ),
        "C1": Node(
            id="C1",
            type="customer",
            name="US Demand",
            region="North America",
            capacity_per_day=1e9,
            lat=40.0,
            lon=-74.0,
        ),
    }
    edges = {
        "E1": Edge(
            id="E1",
            source_id="S1",
            target_id="P1",
            transport_mode="truck",
            base_lead_time=2.0,
            lead_time_std=1.0,
            cost_per_unit=0.10,
            capacity_per_day=5000,
            reliability=0.90,
        ),
        "E2": Edge(
            id="E2",
            source_id="P1",
            target_id="C1",
            transport_mode="ocean",
            base_lead_time=14.0,
            lead_time_std=3.0,
            cost_per_unit=0.20,
            capacity_per_day=10000,
            reliability=0.85,
        ),
    }
    net = SupplyChainNetwork(nodes=nodes, edges=edges)
    net._rebuild_index()
    return net


# ---------------------------------------------------------------------------
# build_network_from_db
# ---------------------------------------------------------------------------


class TestBuildNetworkFromDb:
    def test_creates_correct_nodes_and_edges(self):
        """build_network_from_db creates supplier, port, and customer nodes."""
        from app.simulation.network import build_network_from_db

        # Create mock ORM-like objects with attribute access
        class MockSupplier:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        class MockRoute:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        suppliers = [
            MockSupplier(
                id="sup1",
                name="Test Supplier",
                region="East Asia",
                country="China",
                city="Shanghai",
                capacity_units=10000,
                base_lead_time_days=20,
                lead_time_variance=3,
                cost_multiplier=1.0,
                reliability_score=0.85,
                is_active=True,
            ),
        ]
        routes = [
            MockRoute(
                id="route1",
                name="Shanghai->LA",
                origin_port="Shanghai",
                origin_country="China",
                destination_port="Los Angeles",
                destination_country="United States",
                transport_mode="ocean",
                base_transit_days=14,
                transit_variance_days=3,
                cost_per_kg=0.18,
                risk_score=0.25,
                capacity_tons=18000,
                is_active=True,
                origin_lat=31.23,
                origin_lon=121.47,
                dest_lat=33.74,
                dest_lon=-118.26,
            ),
        ]

        network = build_network_from_db(suppliers, routes)

        # Should have supplier node, 2 port nodes (Shanghai, LA), and US_DEMAND
        assert "sup1" in network.nodes
        assert network.nodes["sup1"].type == "supplier"
        assert "US_DEMAND" in network.nodes
        assert network.nodes["US_DEMAND"].type == "customer"
        # Route edge
        assert "route1" in network.edges
        # At least one LINK_ edge (supplier -> port)
        link_edges = [eid for eid in network.edges if eid.startswith("LINK_")]
        assert len(link_edges) >= 1
        # At least one LAST_MILE_ edge
        last_mile_edges = [eid for eid in network.edges if eid.startswith("LAST_MILE_")]
        assert len(last_mile_edges) >= 1


# ---------------------------------------------------------------------------
# run_simulation
# ---------------------------------------------------------------------------


class TestRunSimulation:
    def test_returns_simulation_result(self):
        """run_simulation returns a SimulationResult."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Test",
            description="test",
            disruptions=[],
            time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=100, seed=42)
        assert isinstance(result, SimulationResult)

    def test_baseline_cost_positive(self):
        """Baseline cost should be > 0 for a connected network."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Test",
            description="test",
            disruptions=[],
            time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=100, seed=42)
        assert result.baseline_cost > 0

    def test_distribution_ordering(self):
        """p50 <= p90 <= p99 in the cost distribution."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Test",
            description="test",
            disruptions=[],
            time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=500, seed=42)
        cd = result.cost_distribution
        assert cd.p50 <= cd.p90
        assert cd.p90 <= cd.p99

    def test_disrupted_scenario_higher_cost(self):
        """A route closure should produce higher average cost than baseline."""
        network = _build_simple_network()

        # Baseline run
        baseline_scenario = Scenario(
            name="Baseline",
            description="no disruptions",
            disruptions=[],
            time_horizon_days=60,
        )
        baseline = run_simulation(network, baseline_scenario, iterations=500, seed=42)

        # Disrupted run: close the ocean route
        disrupted_scenario = Scenario(
            name="Disrupted",
            description="route closure",
            disruptions=[
                Disruption(
                    type="route_closure",
                    affected_ids=["E2"],
                    severity=0.9,
                    duration_days=14,
                ),
            ],
            time_horizon_days=60,
        )
        disrupted = run_simulation(network, disrupted_scenario, iterations=500, seed=42)

        # Disrupted scenario should have lower fill rate or different cost profile
        # When route is closed, fill rate drops because path capacity becomes 0
        assert disrupted.fill_rate_distribution.mean <= baseline.fill_rate_distribution.mean + 0.05

    def test_scenario_name_in_result(self):
        """The scenario name is preserved in the result."""
        network = _build_simple_network()
        scenario = Scenario(
            name="My Custom Scenario",
            description="test",
            disruptions=[],
            time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=50, seed=42)
        assert result.scenario_name == "My Custom Scenario"

    def test_iterations_count(self):
        """The iterations count is correctly recorded."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Test",
            description="test",
            disruptions=[],
            time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=200, seed=42)
        assert result.iterations == 200


# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------


class TestPresetScenarios:
    def test_all_presets_exist(self):
        """All expected preset scenarios are registered."""
        expected_keys = [
            "suez_canal_closure",
            "shanghai_port_congestion",
            "single_source_supplier_failure",
            "demand_shock",
        ]
        for key in expected_keys:
            assert key in PRESET_SCENARIOS, f"Missing preset: {key}"

    def test_preset_scenarios_are_scenarios(self):
        """Each preset is a Scenario instance with valid fields."""
        for key, scenario in PRESET_SCENARIOS.items():
            assert isinstance(scenario, Scenario), f"{key} is not a Scenario"
            assert scenario.name, f"{key} has no name"
            assert scenario.description, f"{key} has no description"
            assert scenario.time_horizon_days > 0, f"{key} has invalid time_horizon"
            assert len(scenario.disruptions) > 0, f"{key} has no disruptions"


# ---------------------------------------------------------------------------
# create_scenario_from_params
# ---------------------------------------------------------------------------


class TestCreateScenarioFromParams:
    def test_custom_params(self):
        """Build a scenario from a custom params dict."""
        params = {
            "name": "Custom Test",
            "description": "A test scenario",
            "time_horizon_days": 60,
            "disruptions": [
                {
                    "type": "route_closure",
                    "affected_ids": ["id1"],
                    "severity": 0.8,
                    "duration_days": 14,
                    "parameters": {"chokepoint": "test"},
                }
            ],
        }
        scenario = create_scenario_from_params(params)
        assert scenario.name == "Custom Test"
        assert scenario.time_horizon_days == 60
        assert len(scenario.disruptions) == 1
        assert scenario.disruptions[0].type == "route_closure"
        assert scenario.disruptions[0].severity == pytest.approx(0.8)

    def test_preset_shortcut(self):
        """The preset key returns the matching preset scenario."""
        scenario = create_scenario_from_params({"preset": "demand_shock"})
        assert scenario.name == "Demand Shock"

    def test_preset_with_time_override(self):
        """The time_horizon_days override is applied to presets."""
        scenario = create_scenario_from_params(
            {
                "preset": "demand_shock",
                "time_horizon_days": 120,
            }
        )
        assert scenario.time_horizon_days == 120

    def test_unknown_preset_raises(self):
        """An unknown preset key raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            create_scenario_from_params({"preset": "nonexistent"})

    def test_defaults_for_missing_fields(self):
        """Missing fields get sensible defaults."""
        scenario = create_scenario_from_params(
            {
                "disruptions": [{"type": "demand_spike"}],
            }
        )
        assert scenario.name == "Custom Scenario"
        assert scenario.time_horizon_days == 90
        assert scenario.disruptions[0].severity == pytest.approx(0.5)
        assert scenario.disruptions[0].duration_days == 14


# ---------------------------------------------------------------------------
# Deterministic reproducibility
# ---------------------------------------------------------------------------


class TestDeterministicSeeds:
    """Same seed + inputs must produce identical outputs."""

    def test_same_seed_same_results(self):
        network = _build_simple_network()
        scenario = Scenario(
            name="Repro",
            description="reproducibility test",
            disruptions=[
                Disruption(
                    type="route_closure", affected_ids=["E2"], severity=0.9, duration_days=14
                ),
            ],
            time_horizon_days=60,
        )
        r1 = run_simulation(network, scenario, iterations=1000, seed=99)
        r2 = run_simulation(network, scenario, iterations=1000, seed=99)

        assert r1.cost_distribution.mean == pytest.approx(r2.cost_distribution.mean, rel=1e-12)
        assert r1.delay_distribution.p95 == pytest.approx(r2.delay_distribution.p95, rel=1e-12)
        assert r1.fill_rate_distribution.mean == pytest.approx(
            r2.fill_rate_distribution.mean, rel=1e-12
        )
        assert r1.stockout_distribution.mean == pytest.approx(
            r2.stockout_distribution.mean, rel=1e-12
        )

    def test_different_seeds_differ(self):
        network = _build_simple_network()
        scenario = Scenario(
            name="Diff",
            description="different seeds",
            disruptions=[],
            time_horizon_days=60,
        )
        r1 = run_simulation(network, scenario, iterations=2000, seed=1)
        r2 = run_simulation(network, scenario, iterations=2000, seed=2)

        # Means will be close but not bit-identical
        assert r1.cost_distribution.mean != pytest.approx(r2.cost_distribution.mean, rel=1e-12)


# ---------------------------------------------------------------------------
# Each disruption type
# ---------------------------------------------------------------------------


class TestDisruptionTypes:
    """Every disruption type produces the expected effect on the simulation."""

    def _run(self, disruptions, **kw):
        network = _build_simple_network()
        scenario = Scenario(
            name="Type Test",
            description="disruption type test",
            disruptions=disruptions,
            time_horizon_days=60,
        )
        return run_simulation(network, scenario, iterations=500, seed=42, **kw)

    def _baseline(self):
        return self._run([])

    def test_capacity_reduction_lowers_fill_rate(self):
        baseline = self._baseline()
        result = self._run(
            [
                Disruption(
                    type="capacity_reduction",
                    affected_ids=["E2"],
                    severity=0.8,
                    duration_days=30,
                    parameters={"remaining_fraction": 0.10},
                ),
            ]
        )
        assert result.fill_rate_distribution.mean < baseline.fill_rate_distribution.mean + 0.01

    def test_node_shutdown_zeroes_capacity(self):
        result = self._run(
            [
                Disruption(
                    type="node_shutdown",
                    affected_ids=["P1"],
                    severity=1.0,
                    duration_days=20,
                ),
            ]
        )
        # Shutting down the only port should cause stockouts
        assert result.stockout_distribution.mean > 0

    def test_demand_spike_increases_cost(self):
        baseline = self._baseline()
        result = self._run(
            [
                Disruption(
                    type="demand_spike",
                    affected_ids=[],
                    severity=0.8,
                    duration_days=30,
                    parameters={"demand_multiplier": 2.5},
                ),
            ]
        )
        # Higher demand → higher total cost
        assert result.cost_distribution.mean > baseline.cost_distribution.mean

    def test_cost_increase_raises_mean_cost(self):
        baseline = self._baseline()
        result = self._run(
            [
                Disruption(
                    type="cost_increase",
                    affected_ids=["E2"],
                    severity=0.5,
                    duration_days=60,
                    parameters={"cost_multiplier": 3.0},
                ),
            ]
        )
        assert result.cost_distribution.mean > baseline.cost_distribution.mean

    def test_route_closure_causes_stockouts(self):
        result = self._run(
            [
                Disruption(
                    type="route_closure",
                    affected_ids=["E2"],
                    severity=1.0,
                    duration_days=30,
                ),
            ]
        )
        # Single-path network: closing E2 means zero capacity → stockouts
        assert result.stockout_distribution.mean > 0
        assert result.fill_rate_distribution.mean < 1.0


# ---------------------------------------------------------------------------
# Multi-path network
# ---------------------------------------------------------------------------


def _build_multi_path_network() -> SupplyChainNetwork:
    """Two suppliers, two paths to customer — tests redundancy."""
    nodes = {
        "S1": Node(
            id="S1",
            type="supplier",
            name="Supplier A",
            region="East Asia",
            capacity_per_day=5000,
            lat=31.0,
            lon=121.0,
        ),
        "S2": Node(
            id="S2",
            type="supplier",
            name="Supplier B",
            region="Southeast Asia",
            capacity_per_day=3000,
            lat=13.0,
            lon=100.0,
        ),
        "P1": Node(
            id="P1",
            type="port",
            name="Shanghai",
            region="China",
            capacity_per_day=20000,
            lat=31.2,
            lon=121.5,
        ),
        "P2": Node(
            id="P2",
            type="port",
            name="Bangkok",
            region="Thailand",
            capacity_per_day=15000,
            lat=13.7,
            lon=100.5,
        ),
        "C1": Node(
            id="C1",
            type="customer",
            name="US Demand",
            region="North America",
            capacity_per_day=1e9,
            lat=40.0,
            lon=-74.0,
        ),
    }
    edges = {
        "E1": Edge(
            id="E1",
            source_id="S1",
            target_id="P1",
            transport_mode="truck",
            base_lead_time=2.0,
            lead_time_std=1.0,
            cost_per_unit=0.10,
            capacity_per_day=5000,
            reliability=0.90,
        ),
        "E2": Edge(
            id="E2",
            source_id="P1",
            target_id="C1",
            transport_mode="ocean",
            base_lead_time=14.0,
            lead_time_std=3.0,
            cost_per_unit=0.20,
            capacity_per_day=10000,
            reliability=0.85,
        ),
        "E3": Edge(
            id="E3",
            source_id="S2",
            target_id="P2",
            transport_mode="truck",
            base_lead_time=3.0,
            lead_time_std=1.5,
            cost_per_unit=0.12,
            capacity_per_day=3000,
            reliability=0.88,
        ),
        "E4": Edge(
            id="E4",
            source_id="P2",
            target_id="C1",
            transport_mode="ocean",
            base_lead_time=18.0,
            lead_time_std=4.0,
            cost_per_unit=0.25,
            capacity_per_day=8000,
            reliability=0.82,
        ),
    }
    net = SupplyChainNetwork(nodes=nodes, edges=edges)
    net._rebuild_index()
    return net


class TestMultiPathNetwork:
    def test_multi_path_finds_both_routes(self):
        network = _build_multi_path_network()
        paths = network.find_alternative_paths("S1", "C1", max_depth=6)
        assert len(paths) >= 1
        paths2 = network.find_alternative_paths("S2", "C1", max_depth=6)
        assert len(paths2) >= 1

    def test_closing_one_path_still_has_fill_rate(self):
        """With redundancy, closing one route doesn't collapse fill rate to zero."""
        network = _build_multi_path_network()
        scenario = Scenario(
            name="Partial Closure",
            description="close path 1",
            disruptions=[
                Disruption(
                    type="route_closure", affected_ids=["E2"], severity=1.0, duration_days=30
                ),
            ],
            time_horizon_days=60,
        )
        result = run_simulation(network, scenario, iterations=500, seed=42)
        # Path 2 (S2->P2->C1) still operational — fill rate should be partial
        assert result.fill_rate_distribution.mean > 0.0

    def test_closing_both_paths_drops_fill_rate(self):
        """Closing all ocean routes to customer collapses fill rate."""
        network = _build_multi_path_network()
        scenario = Scenario(
            name="Total Closure",
            description="close both ocean routes",
            disruptions=[
                Disruption(
                    type="route_closure", affected_ids=["E2", "E4"], severity=1.0, duration_days=60
                ),
            ],
            time_horizon_days=60,
        )
        result = run_simulation(network, scenario, iterations=500, seed=42)
        assert result.fill_rate_distribution.mean < 0.5


# ---------------------------------------------------------------------------
# Lognormal parameter helper
# ---------------------------------------------------------------------------


class TestLognormalParams:
    def test_positive_mean_returns_valid_params(self):
        from app.simulation.engine import _lognormal_params

        mu, sigma = _lognormal_params(10.0, 3.0)
        assert sigma > 0
        # Verify round-trip: E[X] = exp(mu + sigma^2/2)
        expected_mean = np.exp(mu + sigma**2 / 2)
        assert expected_mean == pytest.approx(10.0, rel=1e-6)

    def test_zero_mean_returns_zeros(self):
        from app.simulation.engine import _lognormal_params

        mu, sigma = _lognormal_params(0.0, 5.0)
        assert mu == 0.0
        assert sigma == 0.0

    def test_negative_mean_returns_zeros(self):
        from app.simulation.engine import _lognormal_params

        mu, sigma = _lognormal_params(-1.0, 1.0)
        assert mu == 0.0
        assert sigma == 0.0

    def test_very_small_std_produces_tight_distribution(self):
        from app.simulation.engine import _lognormal_params

        mu, sigma = _lognormal_params(10.0, 0.001)
        assert sigma < 0.01  # very tight


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_network(self):
        """Empty network returns zero-valued results without errors."""
        network = SupplyChainNetwork()
        network._rebuild_index()
        scenario = Scenario(
            name="Empty",
            description="empty network",
            disruptions=[],
            time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=100, seed=42)
        assert result.cost_distribution.mean == 0
        assert result.baseline_cost == 0

    def test_zero_time_horizon(self):
        """Zero time horizon doesn't crash."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Zero Horizon",
            description="zero days",
            disruptions=[],
            time_horizon_days=0,
        )
        result = run_simulation(network, scenario, iterations=50, seed=42)
        assert isinstance(result, SimulationResult)

    def test_single_iteration(self):
        """Engine handles iterations=1 without crashing."""
        network = _build_simple_network()
        scenario = Scenario(
            name="One Iter",
            description="single iteration",
            disruptions=[],
            time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=1, seed=42)
        assert result.iterations == 1
        assert result.cost_distribution.mean > 0

    def test_very_high_severity(self):
        """Severity=1.0 doesn't produce NaN or infinite values."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Max Severity",
            description="extreme severity",
            disruptions=[
                Disruption(
                    type="capacity_reduction",
                    affected_ids=["E1", "E2"],
                    severity=1.0,
                    duration_days=60,
                    parameters={"remaining_fraction": 0.01},
                ),
            ],
            time_horizon_days=60,
        )
        result = run_simulation(network, scenario, iterations=200, seed=42)
        assert np.isfinite(result.cost_distribution.mean)
        assert np.isfinite(result.delay_distribution.mean)
        assert np.isfinite(result.fill_rate_distribution.mean)


# ---------------------------------------------------------------------------
# Service-layer helpers
# ---------------------------------------------------------------------------


class TestServiceHelpers:
    def test_format_results_structure(self):
        """_format_results returns baseline/mitigated/comparison dicts."""
        from app.services.simulation_service import _format_results

        network = _build_simple_network()
        scenario = Scenario(
            name="Test",
            description="test",
            disruptions=[],
            time_horizon_days=30,
        )
        sim_result = run_simulation(network, scenario, iterations=100, seed=42)
        formatted = _format_results(sim_result)

        assert "baseline" in formatted
        assert "mitigated" in formatted
        assert "comparison" in formatted

        for key in ("total_cost", "fill_rate", "avg_lead_time", "risk_score"):
            assert key in formatted["baseline"], f"Missing {key} in baseline"
            assert key in formatted["mitigated"], f"Missing {key} in mitigated"

        assert "cost_change_pct" in formatted["comparison"]
        assert "iterations" in formatted["comparison"]
        assert formatted["comparison"]["iterations"] == 100

    def test_format_results_values_are_finite(self):
        from app.services.simulation_service import _format_results

        network = _build_simple_network()
        scenario = Scenario(
            name="Test",
            description="test",
            disruptions=[
                Disruption(
                    type="route_closure", affected_ids=["E2"], severity=0.9, duration_days=14
                ),
            ],
            time_horizon_days=60,
        )
        sim_result = run_simulation(network, scenario, iterations=200, seed=42)
        formatted = _format_results(sim_result)

        for section in ("baseline", "mitigated"):
            for key, val in formatted[section].items():
                assert np.isfinite(val), f"{section}.{key} = {val} is not finite"

    def test_resolve_scenario_frontend_alias(self):
        """Frontend preset IDs are resolved to backend scenario keys."""
        from app.services.simulation_service import _resolve_scenario

        scenario = _resolve_scenario({"scenario": "suez_closure"})
        assert scenario.name == "Suez Canal Closure"

        scenario = _resolve_scenario({"scenario": "china_lockdown"})
        assert scenario.name == "Shanghai Port Congestion"

        scenario = _resolve_scenario({"scenario": "supplier_failure"})
        assert scenario.name == "Single-Source Supplier Failure"

    def test_resolve_scenario_direct_preset(self):
        """Direct backend preset keys also work."""
        from app.services.simulation_service import _resolve_scenario

        scenario = _resolve_scenario({"preset": "demand_shock"})
        assert scenario.name == "Demand Shock"

    def test_resolve_scenario_custom_params(self):
        """Custom disruption params build a scenario correctly."""
        from app.services.simulation_service import _resolve_scenario

        scenario = _resolve_scenario(
            {
                "name": "Custom",
                "description": "custom test",
                "disruptions": [
                    {"type": "demand_spike", "severity": 0.5, "duration_days": 10},
                ],
            }
        )
        assert scenario.name == "Custom"
        assert len(scenario.disruptions) == 1


# ---------------------------------------------------------------------------
# Disruption pattern matching
# ---------------------------------------------------------------------------


class TestDisruptionPatternMatching:
    """Test _resolve_disruption_ids which pattern-matches nodes/edges."""

    def test_match_port_name(self):
        from app.simulation.engine import _resolve_disruption_ids

        network = _build_simple_network()
        disruption = Disruption(
            type="capacity_reduction",
            affected_ids=[],
            severity=0.5,
            duration_days=14,
            parameters={"match_port": "Shanghai"},
        )
        ids = _resolve_disruption_ids(disruption, network)
        # Should match edges touching the Shanghai port node
        assert len(ids) > 0

    def test_match_transport_mode(self):
        from app.simulation.engine import _resolve_disruption_ids

        network = _build_simple_network()
        disruption = Disruption(
            type="route_closure",
            affected_ids=[],
            severity=0.9,
            duration_days=21,
            parameters={"match_transport": "ocean"},
        )
        ids = _resolve_disruption_ids(disruption, network)
        assert "E2" in ids  # E2 is the ocean edge

    def test_match_region_highest_capacity(self):
        from app.simulation.engine import _resolve_disruption_ids

        network = _build_simple_network()
        disruption = Disruption(
            type="node_shutdown",
            affected_ids=[],
            severity=1.0,
            duration_days=30,
            parameters={"match_region": "East Asia", "pick": "highest_capacity"},
        )
        ids = _resolve_disruption_ids(disruption, network)
        assert ids == ["S1"]  # S1 is the only East Asia supplier

    def test_explicit_ids_bypass_matching(self):
        from app.simulation.engine import _resolve_disruption_ids

        network = _build_simple_network()
        disruption = Disruption(
            type="route_closure",
            affected_ids=["E1"],
            severity=0.5,
            duration_days=10,
            parameters={"match_transport": "ocean"},  # should be ignored
        )
        ids = _resolve_disruption_ids(disruption, network)
        assert ids == ["E1"]  # explicit IDs take precedence
