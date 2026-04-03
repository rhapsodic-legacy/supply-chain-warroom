"""Generate risk events and their impact linkages."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta


def generate_risk_events(
    suppliers: list[dict],
    routes: list[dict],
    seed: int = 42,
) -> tuple[list[dict], list[dict]]:
    """Generate 20 historical + 3 active risk events with impact records.

    Returns (risk_events, risk_event_impacts).
    """
    rng = random.Random(seed)
    events: list[dict] = []
    impacts: list[dict] = []

    now = datetime(2026, 3, 30, 12, 0, 0)

    # Helpers
    asia_suppliers = [s for s in suppliers if s["region"] == "East Asia"]
    south_asia_suppliers = [s for s in suppliers if s["region"] == "South Asia"]  # noqa: F841
    europe_suppliers = [s for s in suppliers if s["region"] == "Europe"]
    shanghai_routes = [r for r in routes if "Shanghai" in r["origin_port"]]
    shenzhen_routes = [r for r in routes if "Shenzhen" in r["origin_port"]]
    rotterdam_routes = [
        r for r in routes if "Rotterdam" in r["origin_port"] or "Rotterdam" in r["destination_port"]
    ]

    # -----------------------------------------------------------------------
    # 3 ACTIVE events (vivid, demo-worthy)
    # -----------------------------------------------------------------------
    # Active 1: Typhoon bearing down on Shanghai
    evt1_id = str(uuid.UUID(int=rng.getrandbits(128)))
    events.append(
        {
            "id": evt1_id,
            "event_type": "weather",
            "title": "Typhoon Meihua bearing down on Shanghai-Ningbo corridor",
            "description": (
                "Super Typhoon Meihua, now Category 4 with sustained winds of 215 km/h, "
                "is tracking northwest toward the Yangtze River Delta. Shanghai port authority "
                "has raised the alert level to Red and suspended all vessel berthing operations. "
                "Approximately 47 container ships are holding at anchorage. Ningbo-Zhoushan port "
                "is also preparing for closure. Inland logistics across Jiangsu and Zhejiang "
                "provinces face severe disruption as highway authorities restrict heavy vehicle "
                "movement. Storm surge warnings issued for coastal warehousing zones."
            ),
            "severity": "critical",
            "severity_score": 0.92,
            "affected_region": "East Asia",
            "started_at": now - timedelta(hours=18),
            "expected_end": now + timedelta(days=5),
            "actual_end": None,
            "is_active": True,
        }
    )
    # Impacts for typhoon: Shanghai routes + 3 East Asia suppliers
    for rt in shanghai_routes[:4]:
        impacts.append(
            _make_impact(rng, evt1_id, "route", rt["id"], rt["name"], rng.uniform(1.8, 3.0))
        )
    for sup in rng.sample(asia_suppliers, k=min(3, len(asia_suppliers))):
        impacts.append(
            _make_impact(rng, evt1_id, "supplier", sup["id"], sup["name"], rng.uniform(1.5, 2.5))
        )

    # Active 2: Labor strike at Rotterdam
    evt2_id = str(uuid.UUID(int=rng.getrandbits(128)))
    events.append(
        {
            "id": evt2_id,
            "event_type": "labor_strike",
            "title": "Dockworker strike paralyzes Port of Rotterdam",
            "description": (
                "The FNV Havens union representing 6,000 dockworkers at Europe's largest port "
                "has launched an indefinite strike over pension reform and automation displacement "
                "concerns. Container throughput has dropped 85% since the action began 3 days ago. "
                "ECT Delta and Euromax terminals are fully idle. APM Terminals Maasvlakte II is "
                "operating at minimal capacity with management staff only. An estimated 120,000 TEU "
                "of cargo is stranded. Maersk and MSC have begun diverting vessels to Antwerp and "
                "Hamburg, causing secondary congestion. Dutch government mediators have been "
                "appointed but unions reject the current offer."
            ),
            "severity": "critical",
            "severity_score": 0.88,
            "affected_region": "Europe",
            "started_at": now - timedelta(days=3),
            "expected_end": now + timedelta(days=11),
            "actual_end": None,
            "is_active": True,
        }
    )
    for rt in rotterdam_routes[:5]:
        impacts.append(
            _make_impact(rng, evt2_id, "route", rt["id"], rt["name"], rng.uniform(2.0, 3.5))
        )
    for sup in rng.sample(europe_suppliers, k=min(2, len(europe_suppliers))):
        impacts.append(
            _make_impact(rng, evt2_id, "supplier", sup["id"], sup["name"], rng.uniform(1.3, 1.8))
        )

    # Active 3: Semiconductor export restrictions from China
    evt3_id = str(uuid.UUID(int=rng.getrandbits(128)))
    events.append(
        {
            "id": evt3_id,
            "event_type": "geopolitical",
            "title": "China imposes emergency export controls on rare earth electronics components",
            "description": (
                "Beijing has issued State Council Decree 2026-41 imposing immediate export licensing "
                "requirements on gallium, germanium, and 14 categories of advanced electronic "
                "components. The decree, effective yesterday, requires suppliers to obtain Ministry "
                "of Commerce approval before shipping — a process estimated at 4-8 weeks. Industry "
                "sources report that MLCC capacitors, power management ICs, and select memory modules "
                "are affected. This directly impacts global electronics and automotive supply chains "
                "dependent on Chinese component manufacturing, which accounts for roughly 62% of "
                "worldwide MLCC production capacity."
            ),
            "severity": "high",
            "severity_score": 0.82,
            "affected_region": "East Asia",
            "started_at": now - timedelta(days=1),
            "expected_end": now + timedelta(days=56),
            "actual_end": None,
            "is_active": True,
        }
    )
    china_suppliers = [s for s in asia_suppliers if s["country"] == "China"]
    for sup in china_suppliers[:4]:
        impacts.append(
            _make_impact(rng, evt3_id, "supplier", sup["id"], sup["name"], rng.uniform(1.6, 2.8))
        )
    for rt in shenzhen_routes[:3] + shanghai_routes[:2]:
        impacts.append(
            _make_impact(rng, evt3_id, "route", rt["id"], rt["name"], rng.uniform(1.3, 2.0))
        )

    # -----------------------------------------------------------------------
    # 20 HISTORICAL (resolved) events
    # -----------------------------------------------------------------------
    _historical_templates = [
        {
            "event_type": "weather",
            "title": "Tropical Storm Noru delays Ho Chi Minh City shipments",
            "description": "Tropical Storm Noru brought heavy rainfall and 90 km/h winds to southern Vietnam, causing a 4-day closure of Cat Lai terminal. 12 vessels were diverted to Singapore for transshipment, adding 6-8 days to transit times for affected cargo.",
            "severity": "high",
            "score": 0.72,
            "region": "East Asia",
            "days_ago": 240,
            "duration": 6,
        },
        {
            "event_type": "port_closure",
            "title": "Shanghai port cyber incident disrupts terminal operations",
            "description": "A ransomware attack on Shanghai International Port Group's terminal operating system caused a 48-hour shutdown of automated container handling at Yangshan Deep Water Port. Manual operations restored partially on day 3.",
            "severity": "high",
            "score": 0.78,
            "region": "East Asia",
            "days_ago": 210,
            "duration": 5,
        },
        {
            "event_type": "supplier_delay",
            "title": "Fire at capacitor production facility in Shenzhen",
            "description": "An electrical fire at a major MLCC manufacturing plant in Shenzhen destroyed two production lines. No casualties reported, but output reduced by 40% for 3 weeks during repairs and safety recertification.",
            "severity": "high",
            "score": 0.68,
            "region": "East Asia",
            "days_ago": 195,
            "duration": 21,
        },
        {
            "event_type": "geopolitical",
            "title": "EU anti-dumping duties on Indian steel components",
            "description": "European Commission imposed provisional anti-dumping duties of 18.4% on certain steel fastener imports from India, effective immediately. Automotive tier-1 suppliers scrambled to recalculate landed costs.",
            "severity": "medium",
            "score": 0.55,
            "region": "South Asia",
            "days_ago": 180,
            "duration": 90,
        },
        {
            "event_type": "demand_spike",
            "title": "Black Friday demand surge overwhelms safety stock",
            "description": "Consumer electronics demand in North America exceeded forecast by 47% during Black Friday week. Safety stock for OLED displays and Li-Ion cells depleted by day 2. Emergency air freight orders triggered.",
            "severity": "high",
            "score": 0.65,
            "region": "North America",
            "days_ago": 125,
            "duration": 12,
        },
        {
            "event_type": "labor_strike",
            "title": "East Coast longshoremen slowdown at Savannah",
            "description": "ILA members at the Port of Savannah engaged in a work-to-rule action protesting automation plans. Container dwell times increased from 3 to 9 days. Trucking queues extended to 6 hours.",
            "severity": "medium",
            "score": 0.58,
            "region": "North America",
            "days_ago": 160,
            "duration": 8,
        },
        {
            "event_type": "weather",
            "title": "Fog blankets English Channel for 5 consecutive days",
            "description": "Unprecedented persistent fog in the Dover Strait caused vessel speed restrictions and pilot service suspensions. Felixstowe and Rotterdam both reported 2-day average delays on inbound vessels.",
            "severity": "medium",
            "score": 0.48,
            "region": "Europe",
            "days_ago": 100,
            "duration": 5,
        },
        {
            "event_type": "port_closure",
            "title": "Long Beach terminal crane collapse",
            "description": "A ship-to-shore gantry crane at Pier J collapsed during high winds, blocking two berths. No injuries but terminal capacity reduced by 30% for 2 weeks during removal and inspection of adjacent cranes.",
            "severity": "high",
            "score": 0.71,
            "region": "North America",
            "days_ago": 85,
            "duration": 14,
        },
        {
            "event_type": "supplier_delay",
            "title": "Power rationing hits Guangdong manufacturing",
            "description": "Provincial authorities in Guangdong imposed rolling power cuts due to summer heat wave straining the grid. Factories limited to 3 operating days per week for 2 weeks, reducing output by approximately 40%.",
            "severity": "high",
            "score": 0.70,
            "region": "East Asia",
            "days_ago": 220,
            "duration": 14,
        },
        {
            "event_type": "geopolitical",
            "title": "US Section 301 tariff review on Vietnamese electronics",
            "description": "USTR announced a review of tariff exemptions for Vietnam-origin electronics assemblies. Uncertainty caused importers to accelerate orders, creating a front-loading surge followed by destocking.",
            "severity": "medium",
            "score": 0.52,
            "region": "East Asia",
            "days_ago": 150,
            "duration": 45,
        },
        {
            "event_type": "weather",
            "title": "Hurricane Helene disrupts Gulf Coast shipping",
            "description": "Hurricane Helene made landfall near Houston as a Category 3 storm. Port of Houston closed for 4 days. Chemical and petrochemical supply chains significantly affected. Inland flooding delayed truck distribution.",
            "severity": "critical",
            "score": 0.90,
            "region": "North America",
            "days_ago": 200,
            "duration": 8,
        },
        {
            "event_type": "demand_spike",
            "title": "EV battery demand spike following subsidy announcement",
            "description": "European governments jointly announced expanded EV purchase subsidies, triggering a 35% spike in Li-Ion cell orders from automotive OEMs. Battery cell suppliers reported 8-week backlogs within days.",
            "severity": "medium",
            "score": 0.60,
            "region": "Europe",
            "days_ago": 140,
            "duration": 30,
        },
        {
            "event_type": "supplier_delay",
            "title": "Quality recall at Mumbai pharmaceutical excipient plant",
            "description": "A batch contamination issue at a major cellulose excipient facility in Mumbai triggered a voluntary recall affecting 3 months of production. FDA and EMA issued import alerts pending investigation.",
            "severity": "high",
            "score": 0.73,
            "region": "South Asia",
            "days_ago": 110,
            "duration": 25,
        },
        {
            "event_type": "port_closure",
            "title": "Suez Canal blocked by grounded bulk carrier",
            "description": "A 200,000 DWT bulk carrier ran aground in the southern section of the Suez Canal, blocking northbound traffic for 3 days. Over 200 vessels queued at both approaches. Asia-Europe transit times extended by 7-12 days for rerouted vessels.",
            "severity": "critical",
            "score": 0.88,
            "region": "East Asia",
            "days_ago": 60,
            "duration": 5,
        },
        {
            "event_type": "labor_strike",
            "title": "Hamburg port workers stage 48-hour warning strike",
            "description": "Ver.di union called a 48-hour warning strike at Hamburg port affecting all container terminals. Throughput dropped to zero during the action. Backlog cleared over the following week.",
            "severity": "medium",
            "score": 0.50,
            "region": "Europe",
            "days_ago": 75,
            "duration": 4,
        },
        {
            "event_type": "weather",
            "title": "Monsoon flooding disrupts Chennai port and rail links",
            "description": "Exceptionally heavy monsoon rainfall caused flooding across Tamil Nadu. Chennai port access roads submerged, rail freight suspended for 5 days. Pharma and automotive shipments ex-Chennai delayed 7-10 days.",
            "severity": "high",
            "score": 0.69,
            "region": "South Asia",
            "days_ago": 170,
            "duration": 8,
        },
        {
            "event_type": "geopolitical",
            "title": "Red Sea security alert elevates insurance premiums",
            "description": "Renewed security incidents in the Red Sea prompted major insurers to classify the region as high-risk. War risk premiums jumped 300%, pushing carriers to route via Cape of Good Hope, adding 12 days to Asia-Europe transit.",
            "severity": "high",
            "score": 0.75,
            "region": "East Asia",
            "days_ago": 90,
            "duration": 60,
        },
        {
            "event_type": "supplier_delay",
            "title": "Semiconductor fab equipment failure in Busan",
            "description": "A critical lithography machine failure at a Korean semiconductor packaging facility halted production of advanced chip substrates. Repair parts sourced from the Netherlands with 3-week lead time.",
            "severity": "medium",
            "score": 0.55,
            "region": "East Asia",
            "days_ago": 130,
            "duration": 22,
        },
        {
            "event_type": "demand_spike",
            "title": "Pharmaceutical demand surge during flu season",
            "description": "An aggressive H3N2 influenza strain drove record demand for ibuprofen API and pre-filled syringes across North America and Europe. Orders exceeded forecast by 60% for 3 weeks.",
            "severity": "high",
            "score": 0.67,
            "region": "North America",
            "days_ago": 50,
            "duration": 21,
        },
        {
            "event_type": "port_closure",
            "title": "Santos port fumigation quarantine halts grain exports",
            "description": "Brazilian agricultural authority MAPA ordered emergency fumigation at Santos port after detection of khapra beetle. All outbound container operations suspended for 4 days. Coffee and consumer goods shipments caught in the hold.",
            "severity": "medium",
            "score": 0.52,
            "region": "South America",
            "days_ago": 40,
            "duration": 5,
        },
    ]

    for tpl in _historical_templates:
        evt_id = str(uuid.UUID(int=rng.getrandbits(128)))
        started = now - timedelta(days=tpl["days_ago"])
        ended = started + timedelta(days=tpl["duration"])

        events.append(
            {
                "id": evt_id,
                "event_type": tpl["event_type"],
                "title": tpl["title"],
                "description": tpl["description"],
                "severity": tpl["severity"],
                "severity_score": tpl["score"],
                "affected_region": tpl["region"],
                "started_at": started,
                "expected_end": ended + timedelta(days=rng.randint(0, 3)),
                "actual_end": ended,
                "is_active": False,
            }
        )

        # Generate 1-4 impacts per historical event
        n_impacts = rng.randint(1, 4)
        region_suppliers = [s for s in suppliers if s["region"] == tpl["region"]]
        region_routes = [r for r in routes if _port_in_region(r["origin_port"], tpl["region"])]

        pool: list[tuple[str, str, str]] = []
        for s in region_suppliers:
            pool.append(("supplier", s["id"], s["name"]))
        for r in region_routes:
            pool.append(("route", r["id"], r["name"]))
        if not pool:
            # Fallback: pick any supplier/route
            s = rng.choice(suppliers)
            pool.append(("supplier", s["id"], s["name"]))

        chosen = rng.sample(pool, k=min(n_impacts, len(pool)))
        for entity_type, entity_id, entity_name in chosen:
            impacts.append(
                _make_impact(
                    rng, evt_id, entity_type, entity_id, entity_name, rng.uniform(1.2, 2.5)
                )
            )

    return events, impacts


def _make_impact(
    rng: random.Random,
    event_id: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    multiplier: float,
) -> dict:
    return {
        "id": str(uuid.UUID(int=rng.getrandbits(128))),
        "risk_event_id": event_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "impact_multiplier": round(multiplier, 2),
    }


def _port_in_region(port_name: str, region: str) -> bool:
    mapping = {
        "East Asia": ["Shanghai", "Shenzhen", "Busan", "Tokyo", "Ho Chi Minh City"],
        "South Asia": ["Mumbai", "Chennai"],
        "Europe": ["Rotterdam", "Hamburg", "Felixstowe", "Genoa"],
        "North America": ["Los Angeles", "Long Beach", "New York/Newark", "Savannah", "Houston"],
        "South America": ["Santos", "Cartagena"],
    }
    return port_name in mapping.get(region, [])
