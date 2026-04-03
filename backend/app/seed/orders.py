"""Generate synthetic purchase orders."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

_STATUS_WEIGHTS = [
    ("pending", 0.15),
    ("confirmed", 0.10),
    ("in_production", 0.10),
    ("shipped", 0.08),
    ("in_transit", 0.07),
    ("customs", 0.05),
    ("delivered", 0.30),
    ("delayed", 0.10),
    ("cancelled", 0.05),
]

_DELAY_REASONS = [
    "Port congestion at origin",
    "Customs documentation incomplete",
    "Supplier raw material shortage",
    "Weather delay en route",
    "Quality inspection hold",
    "Container shortage at port",
    "Vessel schedule slippage",
    "Inland transport breakdown",
    "Regulatory hold at destination",
    "Labor action at transshipment hub",
]


def generate_orders(
    suppliers: list[dict],
    products: list[dict],
    supplier_products: list[dict],
    routes: list[dict],
    seed: int = 42,
) -> list[dict]:
    """Generate 300 historical orders with realistic status distribution."""
    rng = random.Random(seed)
    orders: list[dict] = []

    statuses = [s for s, _ in _STATUS_WEIGHTS]
    weights = [w for _, w in _STATUS_WEIGHTS]

    # Build lookup: supplier_id -> list of (product_id, unit_price)
    sp_map: dict[str, list[tuple[str, float]]] = {}
    for sp in supplier_products:
        sp_map.setdefault(sp["supplier_id"], []).append(
            (sp["product_id"], sp["unit_price"])
        )

    # Filter to active suppliers that have products assigned
    active_suppliers = [s for s in suppliers if s["is_active"] and s["id"] in sp_map]
    if not active_suppliers:
        return orders

    # Ocean routes for matching
    ocean_routes = [r for r in routes if r["transport_mode"] == "ocean"]

    # Reference date for order timeline
    now = datetime(2026, 3, 30, 12, 0, 0)
    hist_start = now - timedelta(days=270)  # 9 months back

    for i in range(300):
        supplier = rng.choice(active_suppliers)
        product_id, unit_price = rng.choice(sp_map[supplier["id"]])

        # Pick a route that originates from the supplier's region (best effort)
        matching_routes = [
            r for r in ocean_routes
            if _region_matches_port(supplier["region"], r["origin_port"])
        ]
        route = rng.choice(matching_routes) if matching_routes else rng.choice(ocean_routes)

        status = rng.choices(statuses, weights=weights, k=1)[0]

        quantity = rng.choice([50, 100, 200, 500, 1000, 2000, 5000])
        total_cost = round(unit_price * quantity, 2)

        # Order date
        days_ago = rng.randint(0, 270)
        ordered_at = hist_start + timedelta(days=days_ago, hours=rng.randint(6, 18))

        # Expected delivery based on supplier lead time + route transit
        lead_days = supplier["base_lead_time_days"] + route["base_transit_days"]
        expected_delivery = ordered_at + timedelta(days=lead_days)

        # Delay logic (correlated with reliability)
        delay_days = 0
        delay_reason = None
        actual_delivery = None

        if status == "delivered":
            # Chance of delay inversely proportional to reliability
            delay_prob = 1.0 - supplier["reliability_score"]
            if rng.random() < delay_prob:
                delay_days = rng.randint(1, 14)
                delay_reason = rng.choice(_DELAY_REASONS)
            actual_delivery = expected_delivery + timedelta(days=delay_days)
        elif status == "delayed":
            delay_days = rng.randint(3, 21)
            delay_reason = rng.choice(_DELAY_REASONS)
            actual_delivery = None  # not yet delivered
        elif status == "cancelled":
            expected_delivery = None
            actual_delivery = None

        order_number = f"PO-2025-{i + 1:04d}"

        orders.append({
            "id": str(uuid.UUID(int=rng.getrandbits(128))),
            "order_number": order_number,
            "product_id": product_id,
            "supplier_id": supplier["id"],
            "route_id": route["id"],
            "quantity": quantity,
            "unit_price": unit_price,
            "total_cost": total_cost,
            "status": status,
            "ordered_at": ordered_at,
            "expected_delivery": expected_delivery,
            "actual_delivery": actual_delivery,
            "delay_days": delay_days,
            "delay_reason": delay_reason,
        })

    return orders


def _region_matches_port(region: str, port_name: str) -> bool:
    """Rough heuristic: does the supplier region correspond to this origin port?"""
    port_region_map = {
        "Shanghai": "East Asia",
        "Shenzhen": "East Asia",
        "Busan": "East Asia",
        "Tokyo": "East Asia",
        "Ho Chi Minh City": "East Asia",
        "Mumbai": "South Asia",
        "Chennai": "South Asia",
        "Rotterdam": "Europe",
        "Hamburg": "Europe",
        "Felixstowe": "Europe",
        "Genoa": "Europe",
        "Santos": "South America",
        "Cartagena": "South America",
        "Los Angeles": "North America",
        "Long Beach": "North America",
        "New York/Newark": "North America",
        "Savannah": "North America",
        "Houston": "North America",
    }
    return port_region_map.get(port_name) == region
