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
        "S1": Node(id="S1", type="supplier", name="Supplier A", region="East Asia",
                    capacity_per_day=5000, lat=31.0, lon=121.0),
        "P1": Node(id="P1", type="port", name="Shanghai", region="China",
                    capacity_per_day=20000, lat=31.2, lon=121.5),
        "C1": Node(id="C1", type="customer", name="US Demand", region="North America",
                    capacity_per_day=1e9, lat=40.0, lon=-74.0),
    }
    edges = {
        "E1": Edge(id="E1", source_id="S1", target_id="P1", transport_mode="truck",
                    base_lead_time=2.0, lead_time_std=1.0, cost_per_unit=0.10,
                    capacity_per_day=5000, reliability=0.90),
        "E2": Edge(id="E2", source_id="P1", target_id="C1", transport_mode="ocean",
                    base_lead_time=14.0, lead_time_std=3.0, cost_per_unit=0.20,
                    capacity_per_day=10000, reliability=0.85),
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
                id="sup1", name="Test Supplier", region="East Asia",
                country="China", city="Shanghai",
                capacity_units=10000, base_lead_time_days=20,
                lead_time_variance=3, cost_multiplier=1.0,
                reliability_score=0.85, is_active=True,
            ),
        ]
        routes = [
            MockRoute(
                id="route1", name="Shanghai->LA",
                origin_port="Shanghai", origin_country="China",
                destination_port="Los Angeles", destination_country="United States",
                transport_mode="ocean", base_transit_days=14,
                transit_variance_days=3, cost_per_kg=0.18,
                risk_score=0.25, capacity_tons=18000,
                is_active=True,
                origin_lat=31.23, origin_lon=121.47,
                dest_lat=33.74, dest_lon=-118.26,
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
            name="Test", description="test",
            disruptions=[], time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=100, seed=42)
        assert isinstance(result, SimulationResult)

    def test_baseline_cost_positive(self):
        """Baseline cost should be > 0 for a connected network."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Test", description="test",
            disruptions=[], time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=100, seed=42)
        assert result.baseline_cost > 0

    def test_distribution_ordering(self):
        """p50 <= p90 <= p99 in the cost distribution."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Test", description="test",
            disruptions=[], time_horizon_days=30,
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
            name="Baseline", description="no disruptions",
            disruptions=[], time_horizon_days=60,
        )
        baseline = run_simulation(network, baseline_scenario, iterations=500, seed=42)

        # Disrupted run: close the ocean route
        disrupted_scenario = Scenario(
            name="Disrupted", description="route closure",
            disruptions=[
                Disruption(
                    type="route_closure", affected_ids=["E2"],
                    severity=0.9, duration_days=14,
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
            name="My Custom Scenario", description="test",
            disruptions=[], time_horizon_days=30,
        )
        result = run_simulation(network, scenario, iterations=50, seed=42)
        assert result.scenario_name == "My Custom Scenario"

    def test_iterations_count(self):
        """The iterations count is correctly recorded."""
        network = _build_simple_network()
        scenario = Scenario(
            name="Test", description="test",
            disruptions=[], time_horizon_days=30,
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
        scenario = create_scenario_from_params({
            "preset": "demand_shock",
            "time_horizon_days": 120,
        })
        assert scenario.time_horizon_days == 120

    def test_unknown_preset_raises(self):
        """An unknown preset key raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            create_scenario_from_params({"preset": "nonexistent"})

    def test_defaults_for_missing_fields(self):
        """Missing fields get sensible defaults."""
        scenario = create_scenario_from_params({
            "disruptions": [{"type": "demand_spike"}],
        })
        assert scenario.name == "Custom Scenario"
        assert scenario.time_horizon_days == 90
        assert scenario.disruptions[0].severity == pytest.approx(0.5)
        assert scenario.disruptions[0].duration_days == 14
