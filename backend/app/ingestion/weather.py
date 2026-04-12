"""Open-Meteo weather integration for port disruption detection.

Checks weather forecasts at major port coordinates and creates risk
events when severe conditions are detected (high winds, heavy rain,
storms).

API: https://api.open-meteo.com/v1/forecast
No API key required. 10,000 requests/day free.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import RiskEvent

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Monitored ports with coordinates
MONITORED_PORTS = [
    {"name": "Shanghai", "lat": 31.23, "lon": 121.47, "region": "East Asia", "country": "China"},
    {"name": "Shenzhen", "lat": 22.54, "lon": 114.06, "region": "East Asia", "country": "China"},
    {"name": "Busan", "lat": 35.18, "lon": 129.08, "region": "East Asia", "country": "South Korea"},
    {"name": "Tokyo", "lat": 35.65, "lon": 139.84, "region": "East Asia", "country": "Japan"},
    {
        "name": "Ho Chi Minh City",
        "lat": 10.77,
        "lon": 106.70,
        "region": "East Asia",
        "country": "Vietnam",
    },
    {"name": "Mumbai", "lat": 18.95, "lon": 72.84, "region": "South Asia", "country": "India"},
    {"name": "Rotterdam", "lat": 51.90, "lon": 4.50, "region": "Europe", "country": "Netherlands"},
    {"name": "Hamburg", "lat": 53.55, "lon": 9.97, "region": "Europe", "country": "Germany"},
    {
        "name": "Los Angeles",
        "lat": 33.74,
        "lon": -118.27,
        "region": "North America",
        "country": "USA",
    },
    {"name": "New York", "lat": 40.67, "lon": -74.04, "region": "North America", "country": "USA"},
    {"name": "Savannah", "lat": 32.08, "lon": -81.09, "region": "North America", "country": "USA"},
    {
        "name": "Santos",
        "lat": -23.95,
        "lon": -46.30,
        "region": "South America",
        "country": "Brazil",
    },
]

# Severity thresholds
WIND_GUST_SEVERE = 90  # km/h — storm force
WIND_GUST_CRITICAL = 120  # km/h — hurricane force
PRECIP_HEAVY = 30  # mm/day — heavy rain
PRECIP_EXTREME = 80  # mm/day — extreme rain

# WMO weather codes indicating severe conditions
SEVERE_WEATHER_CODES = {55, 65, 67, 75, 82, 85, 86, 95, 96, 99}

WMO_DESCRIPTIONS = {
    55: "Heavy drizzle",
    65: "Heavy rain",
    67: "Heavy freezing rain",
    75: "Heavy snowfall",
    82: "Violent rain showers",
    85: "Heavy snow showers",
    86: "Extreme snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


async def fetch_port_weather(port: dict) -> dict | None:
    """Fetch 3-day forecast for a port."""
    params = {
        "latitude": port["lat"],
        "longitude": port["lon"],
        "daily": "weather_code,wind_speed_10m_max,wind_gusts_10m_max,precipitation_sum",
        "current": "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation,weather_code",
        "timezone": "auto",
        "forecast_days": 3,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        logger.warning("Weather fetch failed for %s", port["name"])
        return None


def _assess_severity(
    wind_gust_max: float,
    precip_sum: float,
    weather_code: int,
) -> tuple[str, float, str] | None:
    """Assess whether conditions warrant a risk event.

    Returns (severity, score, description) or None if conditions are normal.
    """
    reasons = []

    if wind_gust_max >= WIND_GUST_CRITICAL:
        reasons.append(f"Hurricane-force gusts of {wind_gust_max:.0f} km/h")
    elif wind_gust_max >= WIND_GUST_SEVERE:
        reasons.append(f"Storm-force gusts of {wind_gust_max:.0f} km/h")

    if precip_sum >= PRECIP_EXTREME:
        reasons.append(f"Extreme rainfall of {precip_sum:.0f}mm")
    elif precip_sum >= PRECIP_HEAVY:
        reasons.append(f"Heavy rainfall of {precip_sum:.0f}mm")

    if weather_code in SEVERE_WEATHER_CODES:
        reasons.append(WMO_DESCRIPTIONS.get(weather_code, f"Severe weather (code {weather_code})"))

    if not reasons:
        return None

    description = ". ".join(reasons)

    if wind_gust_max >= WIND_GUST_CRITICAL or precip_sum >= PRECIP_EXTREME:
        return "critical", 0.90, description
    if wind_gust_max >= WIND_GUST_SEVERE or precip_sum >= PRECIP_HEAVY:
        return "high", 0.70, description
    return "medium", 0.55, description


async def ingest_weather_alerts() -> int:
    """Check weather at all monitored ports and create risk events for severe conditions.

    Returns the number of new risk events created.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    new_events: list[dict] = []

    # Get existing active weather events to avoid duplicates
    async with session_factory() as session:
        result = await session.execute(
            select(RiskEvent.title).where(
                RiskEvent.event_type == "weather",
                RiskEvent.is_active.is_(True),
            )
        )
        active_weather_titles = {row[0].lower() for row in result.all()}

    async with session_factory() as session:
        for port in MONITORED_PORTS:
            weather = await fetch_port_weather(port)
            if not weather:
                continue

            # Check current conditions
            current = weather.get("current", {})
            daily = weather.get("daily", {})

            # Get worst conditions in the 3-day forecast
            max_gust = max(daily.get("wind_gusts_10m_max", [0]) or [0])
            max_precip = max(daily.get("precipitation_sum", [0]) or [0])
            worst_code = max(daily.get("weather_code", [0]) or [0])

            # Also check current conditions
            current_gust = current.get("wind_gusts_10m", 0) or 0
            current_code = current.get("weather_code", 0) or 0

            max_gust = max(max_gust, current_gust)
            worst_code = max(worst_code, current_code)

            assessment = _assess_severity(max_gust, max_precip, worst_code)
            if assessment is None:
                continue

            severity, score, desc = assessment
            title = f"Severe weather alert — Port of {port['name']}"

            # Skip if already active
            if title.lower() in active_weather_titles:
                continue

            event = RiskEvent(
                id=str(uuid.uuid4()),
                event_type="weather",
                title=title,
                description=(
                    f"Open-Meteo weather monitoring detected severe conditions at "
                    f"{port['name']}, {port['country']}. {desc}. "
                    f"Current: {current.get('temperature_2m', '?')}°C, "
                    f"wind {current.get('wind_speed_10m', '?')} km/h. "
                    f"3-day forecast max gust: {max_gust:.0f} km/h, "
                    f"max precipitation: {max_precip:.0f}mm."
                ),
                severity=severity,
                severity_score=score,
                affected_region=port["region"],
                started_at=datetime.utcnow(),
                expected_end=datetime.utcnow() + timedelta(days=3),
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(event)
            created += 1
            new_events.append(
                {
                    "id": event.id,
                    "title": title,
                    "severity": severity,
                    "severity_score": score,
                    "event_type": "weather",
                    "affected_region": port["region"],
                    "description": desc,
                }
            )
            logger.info(
                "Weather: created risk event — %s [%s] (%s)",
                title,
                severity,
                desc,
            )

        if created > 0:
            await session.commit()

    await engine.dispose()

    # Broadcast new weather events to SSE consumers
    if new_events:
        from app.routers.stream import publish_event

        for evt in new_events:
            await publish_event("risk_update", evt)

    logger.info("Weather ingestion complete: %d new events", created)
    return created
