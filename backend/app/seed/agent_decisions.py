"""Generate seeded agent decisions that tell a narrative war-room story."""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta


def generate_agent_decisions(
    risk_events: list[dict],
    orders: list[dict],
    suppliers: list[dict],
    seed: int = 42,
) -> list[dict]:
    """Generate 13 realistic agent decisions responding to the 3 active risk events.

    Returns a list of dicts ready for insertion into the ``agent_decisions`` table.
    """
    rng = random.Random(seed)
    now = datetime(2026, 3, 30, 12, 0, 0)

    # ---- Lookup helpers ----
    def _find_event(substring: str) -> str | None:
        for evt in risk_events:
            if substring.lower() in evt["title"].lower():
                return evt["id"]
        return None

    typhoon_id = _find_event("Typhoon Meihua")
    rotterdam_id = _find_event("Rotterdam")
    export_id = _find_event("export controls")

    order_ids = [o["id"] for o in orders]

    def _pick_orders(n: int) -> str:
        """Return a JSON string of *n* random order IDs."""
        chosen = rng.sample(order_ids, k=min(n, len(order_ids)))
        return json.dumps(chosen)

    china_suppliers = [s for s in suppliers if s.get("country") == "China"]
    china_supplier_names = [s["name"] for s in china_suppliers[:4]]

    decisions: list[dict] = []

    def _add(
        *,
        agent_type: str,
        trigger_event_id: str | None,
        decision_type: str,
        decision_summary: str,
        reasoning: str,
        confidence_score: float,
        affected_orders: str = "[]",
        parameters: str = "{}",
        status: str = "proposed",
        outcome: str | None = None,
        outcome_notes: str | None = None,
        cost_impact: float | None = None,
        time_impact_days: int | None = None,
        decided_at: datetime,
        executed_at: datetime | None = None,
    ) -> None:
        decisions.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "agent_type": agent_type,
                "trigger_event_id": trigger_event_id,
                "decision_type": decision_type,
                "decision_summary": decision_summary,
                "reasoning": reasoning,
                "confidence_score": confidence_score,
                "affected_orders": affected_orders,
                "parameters": parameters,
                "status": status,
                "outcome": outcome,
                "outcome_notes": outcome_notes,
                "cost_impact": cost_impact,
                "time_impact_days": time_impact_days,
                "decided_at": decided_at.isoformat(),
                "executed_at": executed_at.isoformat() if executed_at else None,
                "created_at": decided_at.isoformat(),
            }
        )

    # ===================================================================
    # TYPHOON MEIHUA RESPONSE (5 decisions)
    # ===================================================================

    # 1. risk_monitor: initial assessment (6 hours ago)
    _add(
        agent_type="risk_monitor",
        trigger_event_id=typhoon_id,
        decision_type="risk_assessment",
        decision_summary="Assessed Typhoon Meihua risk as CRITICAL for Shanghai-Ningbo corridor",
        reasoning=(
            "Typhoon Meihua has strengthened to Category 4 with sustained winds of 215 km/h "
            "and is tracking directly toward the Yangtze River Delta. Shanghai port authority "
            "has raised alert to Red and suspended berthing operations. Historical analysis of "
            "comparable events (Typhoon In-fa 2021, Typhoon Lekima 2019) suggests a 5-7 day "
            "full port closure with 12-18 day cargo backlog clearance period."
        ),
        confidence_score=0.94,
        affected_orders=_pick_orders(5),
        parameters=json.dumps(
            {
                "severity": "critical",
                "port_closure_probability": 0.97,
                "estimated_closure_days": 5,
                "backlog_clearance_days": 14,
                "vessels_at_anchorage": 47,
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="Assessment validated by subsequent port closure confirmation.",
        decided_at=now - timedelta(hours=6),
        executed_at=now - timedelta(hours=6),
    )

    # 2. simulation: Monte Carlo on Shanghai closure (5 hours ago)
    _add(
        agent_type="simulation",
        trigger_event_id=typhoon_id,
        decision_type="simulation_run",
        decision_summary="Monte Carlo simulation: Shanghai port closure p90 cost impact $420K",
        reasoning=(
            "Ran 10,000 Monte Carlo iterations modeling full Shanghai port closure for 5-7 days "
            "with stochastic vessel rerouting and demand surge scenarios. The p50 cost impact is "
            "$285K and p90 reaches $420K, driven primarily by emergency air freight for time-critical "
            "electronics shipments. Rerouting via Ningbo is not viable as it falls within the same "
            "storm corridor."
        ),
        confidence_score=0.87,
        affected_orders=_pick_orders(5),
        parameters=json.dumps(
            {
                "simulation_type": "monte_carlo",
                "iterations": 10000,
                "closure_duration_range": [5, 7],
                "p50_cost_usd": 285000,
                "p90_cost_usd": 420000,
                "p99_cost_usd": 610000,
                "primary_driver": "emergency_air_freight",
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="Simulation completed in 14.2s. Results shared with strategy agent.",
        decided_at=now - timedelta(hours=5),
        executed_at=now - timedelta(hours=5),
    )

    # 3. strategy: propose rerouting via HCMC (4 hours ago)
    reroute_orders = _pick_orders(4)
    _add(
        agent_type="strategy",
        trigger_event_id=typhoon_id,
        decision_type="order_reroute",
        decision_summary="Proposed rerouting 4 orders via Ho Chi Minh City, +$18K cost but -12 days delay",
        reasoning=(
            "Analysis of alternative routing options shows Ho Chi Minh City as the optimal "
            "diversion point for Shanghai-bound cargo. Cat Lai terminal has available capacity "
            "and feeder services to Long Beach run twice weekly. The $18K incremental cost "
            "is significantly below the $420K p90 loss from waiting out the typhoon. Transit "
            "time via HCMC adds 4 days but avoids the estimated 16-day total delay."
        ),
        confidence_score=0.82,
        affected_orders=reroute_orders,
        parameters=json.dumps(
            {
                "original_route": "Shanghai - Long Beach",
                "proposed_route": "Ho Chi Minh City - Long Beach",
                "incremental_cost_usd": 18000,
                "transit_delta_days": 4,
                "avoided_delay_days": 16,
                "net_time_saved_days": 12,
            }
        ),
        status="proposed",
        cost_impact=18000.00,
        time_impact_days=-12,
        decided_at=now - timedelta(hours=4),
    )

    # 4. strategy: safety stock trigger (3.5 hours ago)
    _add(
        agent_type="strategy",
        trigger_event_id=typhoon_id,
        decision_type="safety_stock_trigger",
        decision_summary="Triggered safety stock replenishment for 3 critical electronics SKUs",
        reasoning=(
            "With Shanghai port closure expected to last 5+ days and backlog clearance adding "
            "another 14 days, current safety stock levels for OLED display panels, MLCC capacitors, "
            "and Li-Ion battery cells will be exhausted within 8 days at current consumption rates. "
            "Recommending immediate safety stock trigger from regional warehouses in South Korea "
            "and Taiwan to bridge the gap."
        ),
        confidence_score=0.89,
        affected_orders=_pick_orders(3),
        parameters=json.dumps(
            {
                "skus_affected": ["OLED-55-Panel", "MLCC-0402-100nF", "LiIon-21700-5000mAh"],
                "current_stock_days": 8,
                "required_bridge_days": 19,
                "replenishment_sources": [
                    "Incheon regional warehouse",
                    "Taoyuan distribution center",
                ],
            }
        ),
        status="approved",
        cost_impact=42000.00,
        time_impact_days=0,
        decided_at=now - timedelta(hours=3, minutes=30),
    )

    # 5. execution: rerouted orders to HCMC (3 hours ago)
    _add(
        agent_type="execution",
        trigger_event_id=typhoon_id,
        decision_type="order_reroute",
        decision_summary="Executed reroute of 4 orders from Shanghai to Ho Chi Minh City",
        reasoning=(
            "Carrier confirmations received from Maersk and COSCO for rerouting 4 containers "
            "to Cat Lai terminal. Booking references secured for the next HCMC-Long Beach sailing "
            "departing April 1. Customs documentation updated and forwarding agents in HCMC notified. "
            "All 4 orders now tracked on the alternative route."
        ),
        confidence_score=0.91,
        affected_orders=reroute_orders,
        parameters=json.dumps(
            {
                "carrier": "Maersk / COSCO",
                "vessel": "COSCO Shipping Orchid",
                "new_etd": "2026-04-01",
                "new_eta": "2026-04-17",
                "booking_refs": ["MSKU8834201", "MSKU8834202", "COSU7721003", "COSU7721004"],
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="All 4 containers confirmed on COSCO Shipping Orchid departing April 1.",
        cost_impact=18000.00,
        time_impact_days=-12,
        decided_at=now - timedelta(hours=3),
        executed_at=now - timedelta(hours=2, minutes=45),
    )

    # ===================================================================
    # ROTTERDAM STRIKE RESPONSE (4 decisions)
    # ===================================================================

    # 6. risk_monitor: strike assessment (5 hours ago)
    _add(
        agent_type="risk_monitor",
        trigger_event_id=rotterdam_id,
        decision_type="risk_assessment",
        decision_summary="Assessed Rotterdam dockworker strike: 85% throughput drop, indefinite duration",
        reasoning=(
            "FNV Havens union strike has shut down ECT Delta and Euromax terminals completely. "
            "APM Terminals Maasvlakte II operating at minimal capacity with management staff only. "
            "Historical analysis of European port strikes suggests median duration of 11 days. "
            "Union demands on pension reform are structural, reducing likelihood of quick resolution."
        ),
        confidence_score=0.90,
        affected_orders=_pick_orders(5),
        parameters=json.dumps(
            {
                "throughput_drop_pct": 85,
                "terminals_idle": ["ECT Delta", "Euromax"],
                "terminals_minimal": ["APM Maasvlakte II"],
                "stranded_teu": 120000,
                "median_strike_duration_days": 11,
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="Assessment confirmed by port authority operational reports.",
        decided_at=now - timedelta(hours=5),
        executed_at=now - timedelta(hours=5),
    )

    # 7. simulation: disruption model (4.5 hours ago)
    _add(
        agent_type="simulation",
        trigger_event_id=rotterdam_id,
        decision_type="simulation_run",
        decision_summary="Disruption model: p90 delay of 18 days for EU-bound cargo via Rotterdam",
        reasoning=(
            "Ran disruption propagation model across the EU distribution network assuming "
            "Rotterdam remains at 15% capacity. P50 delay is 12 days, p90 reaches 18 days. "
            "Secondary congestion at Antwerp and Hamburg is already materializing as carriers "
            "divert, which compounds delays. Inland barge traffic on the Rhine is unaffected "
            "but cannot compensate for the terminal bottleneck."
        ),
        confidence_score=0.84,
        affected_orders=_pick_orders(4),
        parameters=json.dumps(
            {
                "simulation_type": "disruption_propagation",
                "rotterdam_capacity_pct": 15,
                "p50_delay_days": 12,
                "p90_delay_days": 18,
                "secondary_congestion_ports": ["Antwerp", "Hamburg"],
                "inland_alternatives_viable": False,
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="Model outputs consistent with real-time AIS vessel tracking data.",
        decided_at=now - timedelta(hours=4, minutes=30),
        executed_at=now - timedelta(hours=4, minutes=30),
    )

    # 8. strategy: divert to Hamburg/Antwerp (4 hours ago)
    divert_orders = _pick_orders(3)
    _add(
        agent_type="strategy",
        trigger_event_id=rotterdam_id,
        decision_type="order_reroute",
        decision_summary="Proposed diverting 3 EU-bound shipments to Hamburg, +$32K but -10 days delay",
        reasoning=(
            "Hamburg port has confirmed berth availability for diverted vessels within 48 hours. "
            "While Antwerp is closer, it is experiencing secondary congestion from Rotterdam "
            "diversions. Hamburg offers more reliable capacity and established rail connections "
            "to final destinations in Germany and Central Europe. The $32K premium covers "
            "additional feeder costs and expedited rail freight."
        ),
        confidence_score=0.79,
        affected_orders=divert_orders,
        parameters=json.dumps(
            {
                "original_port": "Rotterdam",
                "proposed_port": "Hamburg",
                "incremental_cost_usd": 32000,
                "avoided_delay_days": 18,
                "new_transit_delta_days": 8,
                "net_time_saved_days": 10,
                "rail_connections": ["Hamburg-Duisburg", "Hamburg-Munich", "Hamburg-Prague"],
            }
        ),
        status="proposed",
        cost_impact=32000.00,
        time_impact_days=-10,
        decided_at=now - timedelta(hours=4),
    )

    # 9. execution: diverted to Hamburg (2 hours ago)
    _add(
        agent_type="execution",
        trigger_event_id=rotterdam_id,
        decision_type="order_reroute",
        decision_summary="Executed diversion of 3 shipments from Rotterdam to Hamburg",
        reasoning=(
            "Secured berth slots at Hamburg HHLA Burchardkai terminal for 3 containers. "
            "MSC confirmed rerouting of 2 containers on MSC Gulsun, and Hapag-Lloyd confirmed "
            "1 container on Hamburg Express. Rail onward bookings made via DB Cargo to Duisburg "
            "and Munich. All documentation updated with German customs pre-clearance."
        ),
        confidence_score=0.88,
        affected_orders=divert_orders,
        parameters=json.dumps(
            {
                "terminal": "HHLA Burchardkai",
                "carriers": ["MSC", "Hapag-Lloyd"],
                "vessels": ["MSC Gulsun", "Hamburg Express"],
                "new_eta_hamburg": "2026-04-03",
                "rail_bookings": ["DB-DUI-20260404", "DB-MUC-20260405"],
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="All 3 containers confirmed and tracked. ETA Hamburg April 3.",
        cost_impact=32000.00,
        time_impact_days=-10,
        decided_at=now - timedelta(hours=2),
        executed_at=now - timedelta(hours=1, minutes=45),
    )

    # ===================================================================
    # EXPORT CONTROLS RESPONSE (3 decisions)
    # ===================================================================

    # 10. risk_monitor: export control assessment (4 hours ago)
    _add(
        agent_type="risk_monitor",
        trigger_event_id=export_id,
        decision_type="risk_assessment",
        decision_summary="Assessed export control impact: 4 Chinese suppliers require MOFCOM licenses",
        reasoning=(
            "State Council Decree 2026-41 imposes immediate export licensing on gallium, germanium, "
            "and 14 categories of electronic components. Four of our Chinese suppliers are directly "
            "affected, covering MLCC capacitors, power management ICs, and memory modules. "
            "License approval is estimated at 4-8 weeks, creating an immediate supply gap for "
            "components representing 62% of our procurement volume in these categories."
        ),
        confidence_score=0.86,
        affected_orders=_pick_orders(4),
        parameters=json.dumps(
            {
                "decree": "State Council Decree 2026-41",
                "affected_suppliers": china_supplier_names[:4],
                "affected_components": [
                    "MLCC capacitors",
                    "power management ICs",
                    "memory modules",
                ],
                "license_approval_weeks": [4, 8],
                "procurement_volume_at_risk_pct": 62,
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="Supplier confirmations received; all 4 have paused shipments pending licensing.",
        decided_at=now - timedelta(hours=4),
        executed_at=now - timedelta(hours=4),
    )

    # 11. strategy: qualify backup suppliers (3 hours ago)
    _add(
        agent_type="strategy",
        trigger_event_id=export_id,
        decision_type="mitigation_plan",
        decision_summary="Recommended qualifying backup suppliers in South Korea and Taiwan for affected components",
        reasoning=(
            "To reduce single-country dependency on China for critical electronic components, "
            "we should fast-track qualification of Samsung Electro-Mechanics (South Korea) for "
            "MLCC capacitors and Nanya Technology (Taiwan) for memory modules. Both suppliers "
            "have existing capacity and can begin sample shipments within 2 weeks. Full "
            "qualification typically takes 6-8 weeks but can be expedited to 4 weeks."
        ),
        confidence_score=0.76,
        affected_orders=_pick_orders(4),
        parameters=json.dumps(
            {
                "backup_suppliers": [
                    {
                        "name": "Samsung Electro-Mechanics",
                        "country": "South Korea",
                        "component": "MLCC capacitors",
                    },
                    {
                        "name": "Nanya Technology",
                        "country": "Taiwan",
                        "component": "memory modules",
                    },
                ],
                "qualification_timeline_weeks": 4,
                "sample_shipment_weeks": 2,
                "estimated_cost_premium_pct": 8,
            }
        ),
        status="proposed",
        cost_impact=None,
        time_impact_days=28,
        decided_at=now - timedelta(hours=3),
    )

    # 12. strategy: safety stock for affected components (2.5 hours ago)
    _add(
        agent_type="strategy",
        trigger_event_id=export_id,
        decision_type="safety_stock_trigger",
        decision_summary="Proposed increasing safety stock for affected MLCC and memory components from non-China sources",
        reasoning=(
            "Current safety stock for MLCC capacitors and memory modules sourced from China "
            "covers only 12 days of demand. With export licensing delays of 4-8 weeks, we need "
            "to immediately procure additional stock from non-restricted sources. Recommend "
            "purchasing 45 days of buffer stock from existing qualified suppliers in Japan and "
            "South Korea at approximately 12% premium."
        ),
        confidence_score=0.83,
        affected_orders=_pick_orders(3),
        parameters=json.dumps(
            {
                "components": ["MLCC-0402-100nF", "MLCC-0603-10uF", "DDR5-4800-16GB"],
                "current_stock_days": 12,
                "target_stock_days": 45,
                "buffer_sources": ["TDK (Japan)", "Samsung Electro-Mechanics (South Korea)"],
                "estimated_premium_pct": 12,
                "estimated_cost_usd": 87000,
            }
        ),
        status="approved",
        cost_impact=87000.00,
        time_impact_days=0,
        decided_at=now - timedelta(hours=2, minutes=30),
    )

    # ===================================================================
    # PROACTIVE (1 decision)
    # ===================================================================

    # 13. risk_monitor: weekly supplier reliability scoring (1 hour ago)
    _add(
        agent_type="risk_monitor",
        trigger_event_id=None,
        decision_type="supplier_status_update",
        decision_summary="Weekly reliability scoring flagged 2 suppliers below performance threshold",
        reasoning=(
            "Automated weekly supplier reliability analysis identified 2 suppliers with composite "
            "scores below the 0.70 threshold: one East Asian supplier dropped to 0.61 due to "
            "consecutive late shipments, and one European supplier fell to 0.67 following quality "
            "rejections. Both have been placed on enhanced monitoring with corrective action "
            "requests issued."
        ),
        confidence_score=0.92,
        affected_orders="[]",
        parameters=json.dumps(
            {
                "scoring_period": "2026-03-23 to 2026-03-30",
                "suppliers_evaluated": len(suppliers),
                "below_threshold": 2,
                "threshold": 0.70,
                "flagged_scores": [0.61, 0.67],
                "actions": ["enhanced_monitoring", "corrective_action_request"],
            }
        ),
        status="executed",
        outcome="success",
        outcome_notes="Corrective action requests sent to both suppliers. Review scheduled for April 6.",
        decided_at=now - timedelta(hours=1),
        executed_at=now - timedelta(hours=1),
    )

    return decisions
