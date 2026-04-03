"""Generate synthetic supplier data."""

from __future__ import annotations

import random
import uuid

from app.seed.constants import REGIONS, PRODUCT_CATALOG

# ---------------------------------------------------------------------------
# Fictional company name components
# ---------------------------------------------------------------------------
_PREFIXES = [
    "Apex", "Nexus", "Zenith", "Vanguard", "Horizon", "Pinnacle", "Meridian",
    "Summit", "Titan", "Atlas", "Orion", "Nova", "Vertex", "Catalyst",
    "Precision", "Stellar", "Phoenix", "Cobalt", "Sapphire", "Crimson",
]
_SUFFIXES_ASIA = [
    "Manufacturing Co.", "Electronics Ltd.", "Industrial Corp.", "Tech Group",
    "Components Co.", "Precision Works", "Global Industries", "Supply Co.",
]
_SUFFIXES_WEST = [
    "Industries GmbH", "Manufacturing S.A.", "Components Ltd.", "Technologies Inc.",
    "Industrial Group", "Precision AG", "Systems B.V.", "Engineering SpA",
]
_SUFFIXES_AMERICAS = [
    "Manufacturing LLC", "Components Inc.", "Industries Corp.", "Supply Co.",
    "Fabrication Ltd.", "Technologies S.A.",
]

# Region-based parameter ranges
_REGION_PARAMS = {
    "East Asia": {"lead_days": (18, 35), "variance": (3, 7), "cost_base": (0.75, 0.90)},
    "South Asia": {"lead_days": (22, 40), "variance": (4, 9), "cost_base": (0.65, 0.85)},
    "Europe": {"lead_days": (10, 22), "variance": (2, 5), "cost_base": (1.05, 1.35)},
    "North America": {"lead_days": (5, 15), "variance": (1, 4), "cost_base": (1.10, 1.45)},
    "South America": {"lead_days": (14, 28), "variance": (3, 7), "cost_base": (0.80, 1.00)},
}

# Distribution targets: 12 East Asia, 3 South Asia, 3 Europe, 2 Americas
_REGION_COUNTS = [
    ("East Asia", 12),
    ("South Asia", 3),
    ("Europe", 3),
    ("North America", 1),
    ("South America", 1),
]


def _pick_name(rng: random.Random, region: str) -> str:
    prefix = rng.choice(_PREFIXES)
    if region in ("East Asia", "South Asia"):
        suffix = rng.choice(_SUFFIXES_ASIA)
    elif region in ("North America", "South America"):
        suffix = rng.choice(_SUFFIXES_AMERICAS)
    else:
        suffix = rng.choice(_SUFFIXES_WEST)
    return f"{prefix} {suffix}"


def generate_suppliers(seed: int = 42) -> list[dict]:
    """Return 20 deterministic supplier dicts."""
    rng = random.Random(seed)
    suppliers: list[dict] = []
    used_names: set[str] = set()

    for region, count in _REGION_COUNTS:
        locations = REGIONS[region]
        for _ in range(count):
            # Unique name
            name = _pick_name(rng, region)
            while name in used_names:
                name = _pick_name(rng, region)
            used_names.add(name)

            loc = rng.choice(locations)
            params = _REGION_PARAMS[region]

            # Reliability: normal distribution centered on 0.82
            reliability = rng.gauss(0.82, 0.12)
            reliability = round(max(0.45, min(0.99, reliability)), 2)

            lead_days = rng.randint(*params["lead_days"])
            variance = rng.randint(*params["variance"])

            # Cost multiplier inversely correlated with lead time
            cost_lo, cost_hi = params["cost_base"]
            lead_lo, lead_hi = params["lead_days"]
            lead_frac = (lead_days - lead_lo) / max(lead_hi - lead_lo, 1)
            cost_mult = round(cost_hi - lead_frac * (cost_hi - cost_lo) + rng.gauss(0, 0.05), 2)
            cost_mult = max(0.60, min(1.60, cost_mult))

            capacity = rng.randint(3000, 25000)

            suppliers.append({
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "name": name,
                "country": loc["country"],
                "region": region,
                "city": loc["city"],
                "reliability_score": reliability,
                "base_lead_time_days": lead_days,
                "lead_time_variance": variance,
                "cost_multiplier": cost_mult,
                "capacity_units": capacity,
                "is_active": True if rng.random() > 0.05 else False,
            })

    return suppliers


def generate_supplier_products(
    suppliers: list[dict], products: list[dict], seed: int = 42
) -> list[dict]:
    """Assign 3-8 products to each supplier. Returns list of supplier_product dicts."""
    rng = random.Random(seed + 100)
    links: list[dict] = []

    # Group products by category
    by_cat: dict[str, list[dict]] = {}
    for p in products:
        by_cat.setdefault(p["category"], []).append(p)

    for sup in suppliers:
        n_products = rng.randint(3, 8)
        # Pick products, biased toward 1-2 categories
        primary_cats = rng.sample(list(by_cat.keys()), k=min(2, len(by_cat)))
        pool: list[dict] = []
        for cat in primary_cats:
            pool.extend(by_cat[cat])
        # Add a few from other categories
        other = [p for p in products if p["category"] not in primary_cats]
        pool.extend(rng.sample(other, k=min(3, len(other))))

        chosen = rng.sample(pool, k=min(n_products, len(pool)))
        for prod in chosen:
            # Unit price = unit_cost * supplier cost_multiplier * small random factor
            price = prod["unit_cost"] * sup["cost_multiplier"] * rng.uniform(0.95, 1.15)
            links.append({
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "supplier_id": sup["id"],
                "product_id": prod["id"],
                "unit_price": round(price, 2),
                "min_order_qty": rng.choice([50, 100, 200, 500, 1000]),
            })

    return links
