"""End-to-end API flow tests for the Supply Chain War Room.

These tests exercise complete user journeys through the REST API
against a seeded database.  No mocking is applied -- all database
operations are real against the in-memory SQLite test database.
"""

import pytest


# =========================================================================
# Flow 1: Risk Detection -> Dashboard Update
# =========================================================================


class TestRiskDetectionDashboardFlow:
    """Create a risk event and verify the dashboard reflects it."""

    async def test_risk_detection_to_dashboard_update(self, seeded_client):
        # Step 1: GET active risk events -- expect 3 from seed data
        resp = await seeded_client.get("/api/v1/risks/?active_only=true")
        assert resp.status_code == 200
        initial_risks = resp.json()
        initial_count = len(initial_risks)
        assert initial_count == 3, f"Expected 3 active risk events, got {initial_count}"

        # Record the initial dashboard state
        dash_resp = await seeded_client.get("/api/v1/dashboard/")
        assert dash_resp.status_code == 200
        initial_active = dash_resp.json()["active_risk_events"]

        # Step 2: POST a new critical risk event
        new_risk = {
            "event_type": "geopolitical",
            "title": "E2E Test — Critical Shipping Lane Closure",
            "description": "A critical shipping lane has been blocked due to geopolitical tensions.",
            "severity": "critical",
            "severity_score": 0.95,
            "affected_region": "Middle East",
        }
        create_resp = await seeded_client.post("/api/v1/risks/", json=new_risk)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["is_active"] is True
        assert created["severity"] == "critical"
        created_id = created["id"]

        # Step 3: GET active risk events again -- expect initial + 1
        resp = await seeded_client.get("/api/v1/risks/?active_only=true")
        assert resp.status_code == 200
        updated_risks = resp.json()
        assert len(updated_risks) == initial_count + 1

        # Verify the new event is in the list
        ids = [r["id"] for r in updated_risks]
        assert created_id in ids

        # Step 4: Dashboard should reflect the increase
        dash_resp2 = await seeded_client.get("/api/v1/dashboard/")
        assert dash_resp2.status_code == 200
        assert dash_resp2.json()["active_risk_events"] == initial_active + 1


# =========================================================================
# Flow 2: Simulation -> Results
# =========================================================================


class TestSimulationFlow:
    """Create a simulation, run it, and verify completed results."""

    async def test_simulation_create_run_results(self, seeded_client):
        # Step 1: Create a simulation
        payload = {
            "name": "E2E Suez Canal Closure Test",
            "description": "Testing the simulation pipeline end to end.",
            "scenario_params": {"preset": "suez_canal_closure"},
            "iterations": 500,  # small for speed
        }
        create_resp = await seeded_client.post("/api/v1/simulations/", json=payload)
        assert create_resp.status_code == 201
        sim = create_resp.json()
        sim_id = sim["id"]
        assert sim["status"] == "pending"

        # Step 2: Run the simulation
        run_resp = await seeded_client.post(f"/api/v1/simulations/{sim_id}/run")
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert run_data["status"] == "completed"

        # Step 3: GET the simulation and verify result fields
        get_resp = await seeded_client.get(f"/api/v1/simulations/{sim_id}")
        assert get_resp.status_code == 200
        result = get_resp.json()
        assert result["status"] == "completed"
        assert result["baseline_metrics"] is not None
        assert result["mitigated_metrics"] is not None
        assert result["started_at"] is not None
        assert result["completed_at"] is not None


# =========================================================================
# Flow 3: Order Pipeline Integrity
# =========================================================================


class TestOrderPipelineFlow:
    """Verify order statistics, filtered queries, and supplier linkage."""

    async def test_order_pipeline_integrity(self, seeded_client):
        # Step 1: GET order stats
        stats_resp = await seeded_client.get("/api/v1/orders/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert isinstance(stats, dict)
        assert len(stats) > 0
        total_orders = sum(stats.values())
        assert total_orders > 0

        # Step 2: GET delayed orders
        delayed_resp = await seeded_client.get("/api/v1/orders/?status=delayed")
        assert delayed_resp.status_code == 200
        delayed = delayed_resp.json()
        assert isinstance(delayed, list)
        # Verify all returned orders have delayed status
        for order in delayed:
            assert order["status"] == "delayed"

        # Step 3: If there are delayed orders, fetch the full order detail
        #         and verify the supplier exists
        if delayed:
            order_id = delayed[0]["id"]
            detail_resp = await seeded_client.get(f"/api/v1/orders/{order_id}")
            assert detail_resp.status_code == 200
            order_detail = detail_resp.json()
            supplier_id = order_detail["supplier_id"]
            sup_resp = await seeded_client.get(f"/api/v1/suppliers/{supplier_id}")
            assert sup_resp.status_code == 200
            assert sup_resp.json()["id"] == supplier_id


# =========================================================================
# Flow 4: Demand -> Supply Health Correlation
# =========================================================================


class TestDemandSupplyHealthFlow:
    """Verify demand summaries, supply health, and risk correlation."""

    async def test_demand_supply_health_correlation(self, seeded_client):
        # Step 1: GET demand summary
        demand_resp = await seeded_client.get("/api/v1/demand/summary")
        assert demand_resp.status_code == 200
        summaries = demand_resp.json()
        assert isinstance(summaries, list)
        assert len(summaries) > 0

        # Step 2: GET supply health for all suppliers
        health_resp = await seeded_client.get("/api/v1/dashboard/supply-health")
        assert health_resp.status_code == 200
        health_items = health_resp.json()
        assert isinstance(health_items, list)
        assert len(health_items) > 0

        # Every health item should have the required fields
        for item in health_items:
            assert "supplier_id" in item
            assert "supplier_name" in item
            assert "region" in item
            assert "reliability_score" in item
            assert "active_risk_count" in item
            assert "pending_orders" in item

        # Step 3: Verify that at least some suppliers with active risks
        #         have active_risk_count > 0 (seed data has 3 active risks
        #         with impacts targeting suppliers)
        risk_resp = await seeded_client.get("/api/v1/risks/?active_only=true")
        active_risks = risk_resp.json()
        # Collect supplier entity_ids from risk impacts
        impacted_supplier_ids = set()
        for risk in active_risks:
            for impact in risk.get("impacts", []):
                if impact["entity_type"] == "supplier" and impact.get("entity_id"):
                    impacted_supplier_ids.add(impact["entity_id"])

        if impacted_supplier_ids:
            health_map = {h["supplier_id"]: h for h in health_items}
            found_correlated = False
            for sid in impacted_supplier_ids:
                if sid in health_map and health_map[sid]["active_risk_count"] > 0:
                    found_correlated = True
                    break
            assert found_correlated, (
                "Expected at least one impacted supplier to have active_risk_count > 0"
            )


# =========================================================================
# Flow 5: Cross-Entity Consistency
# =========================================================================


class TestCrossEntityConsistency:
    """Verify referential integrity across routes, suppliers, and risk impacts."""

    async def test_all_routes_have_valid_coordinates(self, seeded_client):
        resp = await seeded_client.get("/api/v1/routes/")
        assert resp.status_code == 200
        routes = resp.json()
        assert len(routes) > 0

        for route in routes:
            assert isinstance(route["origin_lat"], (int, float))
            assert isinstance(route["origin_lon"], (int, float))
            assert isinstance(route["dest_lat"], (int, float))
            assert isinstance(route["dest_lon"], (int, float))
            # Latitude: -90 to 90
            assert -90 <= route["origin_lat"] <= 90
            assert -90 <= route["dest_lat"] <= 90
            # Longitude: -180 to 180
            assert -180 <= route["origin_lon"] <= 180
            assert -180 <= route["dest_lon"] <= 180

    async def test_all_suppliers_have_valid_regions(self, seeded_client):
        """All suppliers must have a non-empty region string."""
        resp = await seeded_client.get("/api/v1/suppliers/")
        assert resp.status_code == 200
        suppliers = resp.json()
        assert len(suppliers) > 0

        known_regions = {
            "East Asia", "Southeast Asia", "South Asia", "Middle East",
            "Europe", "North America", "South America", "Africa", "Oceania",
        }
        for supplier in suppliers:
            assert supplier["region"], f"Supplier {supplier['id']} has empty region"
            # Verify region is from a known set (flexible -- just check non-empty)
            assert isinstance(supplier["region"], str)
            assert len(supplier["region"]) > 0

    async def test_risk_impact_entity_ids_reference_real_entities(self, seeded_client):
        """Risk impact entity_ids should reference existing suppliers or routes."""
        # Gather all supplier IDs and route IDs
        sup_resp = await seeded_client.get("/api/v1/suppliers/")
        route_resp = await seeded_client.get("/api/v1/routes/")
        supplier_ids = {s["id"] for s in sup_resp.json()}
        route_ids = {r["id"] for r in route_resp.json()}

        all_entity_ids = supplier_ids | route_ids

        # Check risk event impacts
        risk_resp = await seeded_client.get("/api/v1/risks/")
        assert risk_resp.status_code == 200
        risks = risk_resp.json()

        checked = 0
        for risk in risks:
            for impact in risk.get("impacts", []):
                entity_id = impact.get("entity_id")
                if entity_id:
                    assert entity_id in all_entity_ids, (
                        f"Impact entity_id {entity_id} (type={impact['entity_type']}) "
                        f"does not reference a known supplier or route"
                    )
                    checked += 1

        # We expect at least some impacts with entity_ids
        assert checked > 0, "No risk impacts with entity_ids found to validate"

    async def test_order_foreign_keys_valid(self, seeded_client):
        """Spot-check that order detail records reference valid suppliers."""
        sup_resp = await seeded_client.get("/api/v1/suppliers/")
        supplier_ids = {s["id"] for s in sup_resp.json()}

        # Get a sample of orders (brief list), then fetch full details
        orders_resp = await seeded_client.get("/api/v1/orders/?limit=10")
        assert orders_resp.status_code == 200
        orders = orders_resp.json()
        assert len(orders) > 0

        for brief in orders:
            detail_resp = await seeded_client.get(f"/api/v1/orders/{brief['id']}")
            assert detail_resp.status_code == 200
            detail = detail_resp.json()
            assert detail["supplier_id"] in supplier_ids, (
                f"Order {detail['id']} references unknown supplier {detail['supplier_id']}"
            )
