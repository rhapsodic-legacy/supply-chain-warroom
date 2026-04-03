"""Generate shipping route data from trade lane constants."""

from __future__ import annotations

import random
import uuid

from app.seed.constants import PORTS, TRADE_LANES


def generate_routes(seed: int = 42) -> list[dict]:
    """Build route dicts from TRADE_LANES with real port coordinates."""
    rng = random.Random(seed)
    routes: list[dict] = []

    for lane in TRADE_LANES:
        origin_port = PORTS[lane["origin"]]
        dest_port = PORTS[lane["dest"]]

        mode_label = {
            "ocean": "Ocean Freight",
            "air": "Air Freight",
            "rail": "Rail Freight",
            "truck": "Truck",
        }
        name = (
            f"{lane['origin']} \u2192 {lane['dest']} ({mode_label.get(lane['mode'], lane['mode'])})"
        )

        routes.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "name": name,
                "origin_port": lane["origin"],
                "origin_country": origin_port["country"],
                "destination_port": lane["dest"],
                "destination_country": dest_port["country"],
                "transport_mode": lane["mode"],
                "base_transit_days": lane["days"],
                "transit_variance_days": lane["var"],
                "cost_per_kg": lane["cost_kg"],
                "risk_score": lane["risk"],
                "capacity_tons": lane["cap"],
                "is_active": True,
                "origin_lat": origin_port["lat"],
                "origin_lon": origin_port["lon"],
                "dest_lat": dest_port["lat"],
                "dest_lon": dest_port["lon"],
            }
        )

    return routes
