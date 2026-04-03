"""Generate demand signal data with seasonality, trend, and noise."""

from __future__ import annotations

import math
import random
import uuid
from datetime import date, timedelta

from app.seed.constants import SEASONALITY_PROFILES

# Regions where demand is tracked
_DEMAND_REGIONS = ["North America", "Europe", "East Asia"]


def generate_demand(products: list[dict], seed: int = 42) -> list[dict]:
    """Generate weekly demand signals: 9 months historical + 3 months forecast.

    Returns list of demand_signal dicts ready for DB insertion.
    """
    rng = random.Random(seed)
    signals: list[dict] = []

    # Reference date: today-ish (we anchor to a fixed date for determinism)
    today = date(2026, 3, 30)  # Monday of current week
    hist_start = today - timedelta(weeks=39)  # ~9 months back
    forecast_end = today + timedelta(weeks=13)  # ~3 months forward

    # Base weekly demand per product (varies by product cost -- cheap = high volume)
    def _base_demand(product: dict) -> int:
        cost = product["unit_cost"]
        if cost < 1:
            return rng.randint(8000, 20000)
        elif cost < 10:
            return rng.randint(2000, 8000)
        elif cost < 50:
            return rng.randint(500, 3000)
        elif cost < 200:
            return rng.randint(100, 800)
        else:
            return rng.randint(30, 250)

    product_bases = {p["id"]: _base_demand(p) for p in products}

    for product in products:
        category = product["category"]
        seasonality = SEASONALITY_PROFILES.get(category, [1.0] * 12)
        base = product_bases[product["id"]]

        for region in _DEMAND_REGIONS:
            # Region multiplier (NA biggest market)
            region_mult = {"North America": 1.0, "Europe": 0.75, "East Asia": 0.55}.get(region, 0.5)

            week_cursor = hist_start
            week_idx = 0

            while week_cursor < forecast_end:
                month_idx = week_cursor.month - 1  # 0-based
                seasonal = seasonality[month_idx]

                # Slight upward trend: +0.3% per week
                trend = 1.0 + 0.003 * week_idx

                # Weekly pattern: slight dip mid-month
                day_of_month = week_cursor.day
                weekly_pattern = 1.0 - 0.03 * math.sin(2 * math.pi * day_of_month / 30)

                # Noise: 8% standard deviation
                noise = 1.0 + rng.gauss(0, 0.08)

                # 2% chance of demand spike (1.4x - 2.2x)
                spike = 1.0
                if rng.random() < 0.02:
                    spike = rng.uniform(1.4, 2.2)

                forecast_qty = int(
                    base * region_mult * seasonal * trend * weekly_pattern * noise * spike
                )
                forecast_qty = max(1, forecast_qty)

                is_historical = week_cursor <= today

                if is_historical:
                    # Actuals have their own noise relative to forecast
                    actual_noise = 1.0 + rng.gauss(0, 0.06)
                    actual_qty = max(1, int(forecast_qty * actual_noise))
                    variance_pct = (
                        round(((actual_qty - forecast_qty) / forecast_qty) * 100, 2)
                        if forecast_qty
                        else 0.0
                    )
                else:
                    actual_qty = None
                    variance_pct = None

                signals.append(
                    {
                        "id": str(uuid.UUID(int=rng.getrandbits(128))),
                        "product_id": product["id"],
                        "region": region,
                        "signal_date": week_cursor,
                        "forecast_qty": forecast_qty,
                        "actual_qty": actual_qty,
                        "variance_pct": variance_pct,
                    }
                )

                week_cursor += timedelta(weeks=1)
                week_idx += 1

    return signals
