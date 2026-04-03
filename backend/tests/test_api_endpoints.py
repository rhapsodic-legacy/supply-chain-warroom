"""Tests for all REST API endpoints against a seeded database."""


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_health_returns_200(self, seeded_client):
        resp = await seeded_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    async def test_dashboard_overview(self, seeded_client):
        resp = await seeded_client.get("/api/v1/dashboard/")
        assert resp.status_code == 200
        data = resp.json()
        # Verify all DashboardOverview fields are present
        for field in [
            "total_orders",
            "active_orders",
            "total_suppliers",
            "active_suppliers",
            "active_risk_events",
            "critical_risk_events",
            "avg_fill_rate",
            "total_revenue",
        ]:
            assert field in data, f"Missing field: {field}"
        assert data["total_orders"] > 0

    async def test_supply_health(self, seeded_client):
        resp = await seeded_client.get("/api/v1/dashboard/supply-health")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        item = data[0]
        assert "supplier_id" in item
        assert "reliability_score" in item


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------


class TestSuppliers:
    async def test_list_suppliers(self, seeded_client):
        resp = await seeded_client.get("/api/v1/suppliers/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 20

    async def test_get_supplier_valid(self, seeded_client):
        # First get the list, then fetch one by ID
        list_resp = await seeded_client.get("/api/v1/suppliers/")
        suppliers = list_resp.json()
        supplier_id = suppliers[0]["id"]

        resp = await seeded_client.get(f"/api/v1/suppliers/{supplier_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == supplier_id

    async def test_get_supplier_not_found(self, seeded_client):
        resp = await seeded_client.get("/api/v1/suppliers/nonexistent-id-000")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class TestOrders:
    async def test_list_orders(self, seeded_client):
        resp = await seeded_client.get("/api/v1/orders/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_order_stats(self, seeded_client):
        resp = await seeded_client.get("/api/v1/orders/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Should contain at least some status keys
        assert len(data) > 0


# ---------------------------------------------------------------------------
# Risks
# ---------------------------------------------------------------------------


class TestRisks:
    async def test_list_risk_events(self, seeded_client):
        resp = await seeded_client.get("/api/v1/risks/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Each risk event should have impacts
        item = data[0]
        assert "impacts" in item

    async def test_active_only_filter(self, seeded_client):
        resp = await seeded_client.get("/api/v1/risks/?active_only=true")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # All returned events should be active
        for event in data:
            assert event["is_active"] is True
        assert len(data) == 3  # 3 active events in seed data


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class TestRoutes:
    async def test_list_routes(self, seeded_client):
        resp = await seeded_client.get("/api/v1/routes/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 36

    async def test_routes_have_coordinates(self, seeded_client):
        resp = await seeded_client.get("/api/v1/routes/")
        data = resp.json()
        for route in data:
            assert "origin_lat" in route
            assert "origin_lon" in route
            assert "dest_lat" in route
            assert "dest_lon" in route


# ---------------------------------------------------------------------------
# Demand
# ---------------------------------------------------------------------------


class TestDemand:
    async def test_list_demand(self, seeded_client):
        resp = await seeded_client.get("/api/v1/demand/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_demand_summary(self, seeded_client):
        resp = await seeded_client.get("/api/v1/demand/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------


class TestSimulations:
    async def test_list_simulations(self, seeded_client):
        resp = await seeded_client.get("/api/v1/simulations/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # May be empty since seed data doesn't include simulations


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class TestAgents:
    async def test_list_decisions(self, seeded_client):
        resp = await seeded_client.get("/api/v1/agents/decisions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # May be empty since seed data doesn't include agent decisions
