"""Generate seeded agent memories — institutional knowledge from past decisions."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta


def generate_agent_memories(
    risk_events: list[dict],
    agent_decisions: list[dict],
    seed: int = 42,
) -> list[dict]:
    """Generate realistic agent memories representing lessons learned.

    These represent institutional knowledge accumulated over previous quarters,
    giving agents historical context to reference in new situations.
    """
    rng = random.Random(seed)
    now = datetime(2026, 3, 30, 12, 0, 0)

    # Link to actual decisions where possible
    decision_ids = [d["id"] for d in agent_decisions]
    event_ids = [e["id"] for e in risk_events if e.get("is_active")]

    memories: list[dict] = []

    def _add(
        *,
        agent_type: str,
        category: str,
        situation: str,
        action_taken: str,
        outcome: str,
        lesson: str,
        confidence_score: float,
        affected_region: str | None = None,
        severity: str | None = None,
        risk_type: str | None = None,
        cost_impact: float | None = None,
        time_impact_days: int | None = None,
        decision_id: str | None = None,
        trigger_event_id: str | None = None,
        occurrence_count: int = 1,
        days_ago: int = 0,
    ) -> None:
        created = now - timedelta(days=days_ago, hours=rng.randint(0, 12))
        memories.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "agent_type": agent_type,
                "decision_id": decision_id,
                "trigger_event_id": trigger_event_id,
                "category": category,
                "affected_region": affected_region,
                "severity": severity,
                "risk_type": risk_type,
                "situation": situation,
                "action_taken": action_taken,
                "outcome": outcome,
                "lesson": lesson,
                "confidence_score": confidence_score,
                "cost_impact": cost_impact,
                "time_impact_days": time_impact_days,
                "occurrence_count": occurrence_count,
                "last_referenced_at": (now - timedelta(days=rng.randint(0, days_ago))).isoformat()
                if days_ago > 3
                else None,
                "created_at": created.isoformat(),
                "updated_at": created.isoformat(),
            }
        )

    # ===================================================================
    # Historical lessons (from previous quarters)
    # ===================================================================

    # 1. Port closure — Suez Canal blockage Q1 2025
    _add(
        agent_type="strategy",
        category="port_closure",
        situation=(
            "Suez Canal blocked by grounded container vessel for 6 days. "
            "All Asia-Europe traffic halted, 400+ vessels queued."
        ),
        action_taken=(
            "Rerouted 12 shipments via Cape of Good Hope. Activated safety stock "
            "from regional warehouses. Pre-booked air freight for 3 critical orders."
        ),
        outcome="effective",
        lesson=(
            "Cape of Good Hope rerouting adds 10-14 days but is reliable during Suez closures. "
            "Air freight should be reserved for critical components only — cost per kg is 8-12x sea. "
            "Safety stock of 21+ days for critical SKUs provides adequate buffer."
        ),
        confidence_score=0.92,
        affected_region="Middle East",
        severity="critical",
        risk_type="logistics",
        cost_impact=340000.00,
        time_impact_days=12,
        occurrence_count=3,
        days_ago=90,
    )

    # 2. Supplier failure — Shenzhen factory fire Q4 2024
    _add(
        agent_type="strategy",
        category="supplier_failure",
        situation=(
            "Primary MLCC capacitor supplier in Shenzhen had factory fire. "
            "Production halted for 8 weeks. 35% of our MLCC supply affected."
        ),
        action_taken=(
            "Fast-tracked qualification of backup supplier in South Korea (Samsung EM). "
            "Split orders across 3 alternative sources to avoid new single-point dependency."
        ),
        outcome="effective",
        lesson=(
            "Multi-source qualification should be completed BEFORE a crisis. "
            "Lead time for emergency supplier qualification is 4-6 weeks minimum. "
            "Splitting across 3+ sources is more resilient than shifting to one backup."
        ),
        confidence_score=0.88,
        affected_region="East Asia",
        severity="high",
        risk_type="supplier",
        cost_impact=215000.00,
        time_impact_days=14,
        occurrence_count=2,
        days_ago=120,
    )

    # 3. Weather disruption — European winter storm Q1 2025
    _add(
        agent_type="risk_monitor",
        category="weather_disruption",
        situation=(
            "Severe winter storm across Northern Europe caused widespread port "
            "congestion at Hamburg and Rotterdam. 3-day terminal shutdowns."
        ),
        action_taken=(
            "Diverted 5 inbound shipments to Mediterranean ports (Barcelona, Genoa). "
            "Arranged truck-rail intermodal for last-mile delivery to central Europe."
        ),
        outcome="partially_effective",
        lesson=(
            "Mediterranean port diversion works for Western Europe but adds 5-7 days "
            "for Central/Eastern European destinations due to limited rail connections. "
            "Hamburg recovers faster than Rotterdam after weather events — prefer Hamburg diversions."
        ),
        confidence_score=0.75,
        affected_region="Europe",
        severity="high",
        risk_type="weather",
        cost_impact=78000.00,
        time_impact_days=6,
        occurrence_count=2,
        days_ago=60,
    )

    # 4. Demand spike — Unexpected order surge Q2 2025
    _add(
        agent_type="strategy",
        category="demand_spike",
        situation=(
            "Unexpected 3x demand surge for automotive sensors after competitor recall. "
            "Existing inventory depleted in 4 days. 2 suppliers at max capacity."
        ),
        action_taken=(
            "Expedited orders at premium pricing from all qualified suppliers. "
            "Negotiated capacity reservation agreement for future surge scenarios."
        ),
        outcome="partially_effective",
        lesson=(
            "Demand spike response is limited by supplier capacity, not just our ordering speed. "
            "Capacity reservation agreements (pay 5% premium for guaranteed surge capacity) "
            "are cost-effective insurance. Stockout cost was 4x the premium we could have paid."
        ),
        confidence_score=0.80,
        affected_region="North America",
        severity="high",
        risk_type="demand",
        cost_impact=156000.00,
        time_impact_days=8,
        occurrence_count=1,
        days_ago=45,
    )

    # 5. Geopolitical — Taiwan Strait tensions Q3 2025
    _add(
        agent_type="risk_monitor",
        category="geopolitical",
        situation=(
            "Military exercises in Taiwan Strait disrupted shipping lanes for 10 days. "
            "Major carriers suspended East Asia-Pacific routes. Insurance premiums spiked 40%."
        ),
        action_taken=(
            "Pre-positioned 30 days of critical component inventory in Vietnam warehouse. "
            "Established secondary supplier relationships in India and Malaysia as geographic hedge."
        ),
        outcome="effective",
        lesson=(
            "Geographic diversification outside the Taiwan Strait corridor is essential. "
            "Vietnam and Malaysia are viable secondary sourcing regions for semiconductors. "
            "Pre-positioning inventory in neutral locations reduces exposure to specific corridor risks. "
            "Insurance hedging should be activated when tensions exceed threshold, not after disruption."
        ),
        confidence_score=0.85,
        affected_region="East Asia",
        severity="critical",
        risk_type="geopolitical",
        cost_impact=420000.00,
        time_impact_days=5,
        occurrence_count=2,
        days_ago=75,
    )

    # 6. Logistics bottleneck — US West Coast port congestion Q4 2024
    _add(
        agent_type="execution",
        category="logistics_bottleneck",
        situation=(
            "Long Beach and LA ports experienced 2-week vessel queue. "
            "Average wait time 8 days before berth assignment."
        ),
        action_taken=(
            "Diverted 8 containers to Oakland and Seattle-Tacoma. "
            "Used intermodal rail to reach Southern California destinations."
        ),
        outcome="effective",
        lesson=(
            "Pacific Northwest ports (Seattle-Tacoma, Oakland) are reliable overflow options "
            "when LA/Long Beach are congested. Rail intermodal adds 2-3 days but avoids "
            "the full queue delay. Booking diversions within 48 hours of congestion onset "
            "is critical — capacity fills fast when multiple shippers divert simultaneously."
        ),
        confidence_score=0.90,
        affected_region="North America",
        severity="medium",
        risk_type="logistics",
        cost_impact=45000.00,
        time_impact_days=-5,
        occurrence_count=3,
        days_ago=150,
    )

    # 7. Current typhoon response lesson (from current decisions)
    _add(
        agent_type="strategy",
        category="weather_disruption",
        situation=(
            "Typhoon Meihua approaching Shanghai with Category 4 intensity. "
            "Port closure imminent, 47 vessels at anchorage."
        ),
        action_taken=(
            "Rerouted 4 orders via Ho Chi Minh City. Triggered safety stock "
            "replenishment from South Korea and Taiwan warehouses."
        ),
        outcome="pending",
        lesson=(
            "Ho Chi Minh City is a viable diversion point for Shanghai-bound cargo. "
            "Cat Lai terminal has feeder services to Long Beach twice weekly. "
            "Cost premium of $18K for 4 containers is well below the p90 loss estimate of $420K."
        ),
        confidence_score=0.82,
        affected_region="East Asia",
        severity="critical",
        risk_type="weather",
        cost_impact=18000.00,
        time_impact_days=-12,
        decision_id=decision_ids[2] if len(decision_ids) > 2 else None,
        trigger_event_id=event_ids[0] if event_ids else None,
        occurrence_count=1,
        days_ago=0,
    )

    # 8. Rotterdam strike lesson (from current decisions)
    _add(
        agent_type="strategy",
        category="port_closure",
        situation=(
            "FNV Havens union strike at Rotterdam shut down ECT Delta and Euromax. "
            "85% throughput reduction, indefinite duration."
        ),
        action_taken=(
            "Diverted 3 shipments to Hamburg. Avoided Antwerp due to secondary congestion."
        ),
        outcome="pending",
        lesson=(
            "Hamburg is preferred over Antwerp for Rotterdam diversions — Antwerp fills up fast "
            "as the obvious first choice. Hamburg has better rail connections to Central Europe. "
            "Strike duration is harder to predict than weather events — build in extra buffer."
        ),
        confidence_score=0.79,
        affected_region="Europe",
        severity="high",
        risk_type="logistics",
        cost_impact=32000.00,
        time_impact_days=-10,
        decision_id=decision_ids[7] if len(decision_ids) > 7 else None,
        trigger_event_id=event_ids[1] if len(event_ids) > 1 else None,
        occurrence_count=1,
        days_ago=0,
    )

    # 9. Export control lesson (from current decisions)
    _add(
        agent_type="risk_monitor",
        category="geopolitical",
        situation=(
            "China State Council Decree 2026-41 imposed export licensing on electronic components. "
            "4 suppliers paused shipments. 62% procurement volume at risk."
        ),
        action_taken=(
            "Initiated backup supplier qualification in South Korea and Taiwan. "
            "Procured 45 days of buffer stock from non-restricted sources."
        ),
        outcome="pending",
        lesson=(
            "Geopolitical export controls can activate with zero notice. "
            "Maintaining pre-qualified alternative suppliers in different jurisdictions is essential. "
            "Buffer stock for components with single-country concentration should be 30+ days."
        ),
        confidence_score=0.86,
        affected_region="East Asia",
        severity="critical",
        risk_type="geopolitical",
        cost_impact=87000.00,
        time_impact_days=28,
        decision_id=decision_ids[10] if len(decision_ids) > 10 else None,
        trigger_event_id=event_ids[2] if len(event_ids) > 2 else None,
        occurrence_count=1,
        days_ago=0,
    )

    return memories
