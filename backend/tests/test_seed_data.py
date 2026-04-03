"""Tests for the synthetic seed data generators."""

import uuid

import pytest

from app.seed.constants import PRODUCT_CATALOG
from app.seed.orders import generate_orders
from app.seed.risk_events import generate_risk_events
from app.seed.routes import generate_routes
from app.seed.suppliers import generate_supplier_products, generate_suppliers


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------


class TestGenerateSuppliers:
    def test_returns_20_suppliers(self):
        suppliers = generate_suppliers(seed=42)
        assert len(suppliers) == 20

    def test_required_fields_present(self):
        suppliers = generate_suppliers(seed=42)
        required_fields = [
            "id",
            "name",
            "country",
            "region",
            "city",
            "reliability_score",
            "base_lead_time_days",
            "lead_time_variance",
            "cost_multiplier",
            "capacity_units",
            "is_active",
        ]
        for s in suppliers:
            for field in required_fields:
                assert field in s, f"Missing field '{field}' in supplier {s.get('name', '?')}"

    def test_reliability_score_range(self):
        suppliers = generate_suppliers(seed=42)
        for s in suppliers:
            assert 0.45 <= s["reliability_score"] <= 0.99, (
                f"Supplier {s['name']} reliability {s['reliability_score']} out of range"
            )

    def test_unique_ids(self):
        suppliers = generate_suppliers(seed=42)
        ids = [s["id"] for s in suppliers]
        assert len(ids) == len(set(ids))

    def test_deterministic_with_same_seed(self):
        a = generate_suppliers(seed=42)
        b = generate_suppliers(seed=42)
        assert a == b


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class TestGenerateRoutes:
    def test_returns_36_routes(self):
        routes = generate_routes(seed=42)
        assert len(routes) == 36

    def test_valid_latitudes(self):
        routes = generate_routes(seed=42)
        for r in routes:
            assert -90 <= r["origin_lat"] <= 90, f"Invalid origin_lat: {r['origin_lat']}"
            assert -90 <= r["dest_lat"] <= 90, f"Invalid dest_lat: {r['dest_lat']}"

    def test_valid_longitudes(self):
        routes = generate_routes(seed=42)
        for r in routes:
            assert -180 <= r["origin_lon"] <= 180, f"Invalid origin_lon: {r['origin_lon']}"
            assert -180 <= r["dest_lon"] <= 180, f"Invalid dest_lon: {r['dest_lon']}"

    def test_transport_modes(self):
        routes = generate_routes(seed=42)
        modes = {r["transport_mode"] for r in routes}
        assert "ocean" in modes
        assert "air" in modes
        assert "rail" in modes

    def test_route_has_required_fields(self):
        routes = generate_routes(seed=42)
        required = [
            "id",
            "name",
            "origin_port",
            "origin_country",
            "destination_port",
            "destination_country",
            "transport_mode",
            "base_transit_days",
            "transit_variance_days",
            "cost_per_kg",
            "risk_score",
            "capacity_tons",
            "is_active",
            "origin_lat",
            "origin_lon",
            "dest_lat",
            "dest_lon",
        ]
        for r in routes:
            for field in required:
                assert field in r, f"Missing field '{field}' in route {r.get('name', '?')}"


# ---------------------------------------------------------------------------
# Risk events
# ---------------------------------------------------------------------------


class TestGenerateRiskEvents:
    def _generate(self):
        suppliers = generate_suppliers(seed=42)
        routes = generate_routes(seed=42)
        return generate_risk_events(suppliers, routes, seed=42)

    def test_returns_events_and_impacts(self):
        events, impacts = self._generate()
        assert isinstance(events, list)
        assert isinstance(impacts, list)
        assert len(events) > 0
        assert len(impacts) > 0

    def test_three_active_events(self):
        events, _ = self._generate()
        active = [e for e in events if e["is_active"]]
        assert len(active) == 3

    def test_events_have_severity(self):
        events, _ = self._generate()
        valid_severities = {"low", "medium", "high", "critical"}
        for e in events:
            assert e["severity"] in valid_severities, f"Invalid severity: {e['severity']}"

    def test_impacts_reference_valid_events(self):
        events, impacts = self._generate()
        event_ids = {e["id"] for e in events}
        for imp in impacts:
            assert imp["risk_event_id"] in event_ids


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class TestGenerateOrders:
    def _generate(self):
        import random as _random

        suppliers = generate_suppliers(seed=42)
        rng = _random.Random(42)
        products = []
        for p in PRODUCT_CATALOG:
            products.append({"id": str(uuid.UUID(int=rng.getrandbits(128))), **p})
        supplier_products = generate_supplier_products(suppliers, products, seed=42)
        routes = generate_routes(seed=42)
        return generate_orders(suppliers, products, supplier_products, routes, seed=42)

    def test_returns_300_orders(self):
        orders = self._generate()
        assert len(orders) == 300

    def test_valid_statuses(self):
        orders = self._generate()
        valid = {
            "pending",
            "confirmed",
            "in_production",
            "shipped",
            "in_transit",
            "customs",
            "delivered",
            "delayed",
            "cancelled",
        }
        for o in orders:
            assert o["status"] in valid, f"Invalid status: {o['status']}"

    def test_orders_have_required_fields(self):
        orders = self._generate()
        required = [
            "id",
            "order_number",
            "product_id",
            "supplier_id",
            "route_id",
            "quantity",
            "unit_price",
            "total_cost",
            "status",
        ]
        for o in orders:
            for field in required:
                assert field in o, f"Missing field '{field}' in order {o.get('order_number', '?')}"

    def test_total_cost_matches_quantity_times_price(self):
        orders = self._generate()
        for o in orders:
            expected = round(o["unit_price"] * o["quantity"], 2)
            assert o["total_cost"] == pytest.approx(expected, rel=1e-2)


# ---------------------------------------------------------------------------
# Product catalog
# ---------------------------------------------------------------------------


class TestProductCatalog:
    def test_has_25_products(self):
        assert len(PRODUCT_CATALOG) == 25

    def test_four_categories(self):
        categories = {p["category"] for p in PRODUCT_CATALOG}
        assert categories == {"electronics", "automotive", "pharma", "consumer_goods"}

    def test_products_have_required_fields(self):
        required = [
            "sku",
            "name",
            "category",
            "unit_cost",
            "weight_kg",
            "is_critical",
            "description",
        ]
        for p in PRODUCT_CATALOG:
            for field in required:
                assert field in p, f"Missing field '{field}' in product {p.get('sku', '?')}"

    def test_unit_costs_positive(self):
        for p in PRODUCT_CATALOG:
            assert p["unit_cost"] > 0, f"Product {p['sku']} has non-positive cost"
