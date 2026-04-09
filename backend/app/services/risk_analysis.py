"""Automated risk analysis pipeline.

Runs after each ingestion cycle to triage new risk events, re-score
affected suppliers, detect threshold crossings, and raise alerts — all
pushed to connected dashboards via SSE.

Two layers:
1. Rule-based triage (always runs, no API key needed)
2. Optional Claude agent deep-analysis for high/critical events
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, RiskEvent, Supplier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Supplier composite risk score above which we auto-generate an alert
SUPPLIER_RISK_ALERT_THRESHOLD = 0.65

# If a region accumulates this many active high/critical events, escalate
REGIONAL_ESCALATION_THRESHOLD = 3

# How far back to look for "new" events (matches ingestion cycle interval)
NEW_EVENT_WINDOW_MINUTES = 35


# ---------------------------------------------------------------------------
# Supplier risk scoring (mirrors risk_tools.score_suppliers but returns raw)
# ---------------------------------------------------------------------------


async def _score_suppliers(db: AsyncSession) -> list[dict]:
    """Compute composite risk scores for all active suppliers."""
    result = await db.execute(
        select(Supplier).where(Supplier.is_active.is_(True))
    )
    suppliers = result.scalars().all()

    # Active risk events by region
    risk_result = await db.execute(
        select(RiskEvent.affected_region, func.count(RiskEvent.id))
        .where(RiskEvent.is_active.is_(True))
        .group_by(RiskEvent.affected_region)
    )
    risk_counts: dict[str | None, int] = dict(risk_result.all())

    # Order exposure by supplier
    exposure_result = await db.execute(
        select(Order.supplier_id, func.sum(Order.total_cost))
        .where(Order.status.in_(["pending", "in_transit", "processing"]))
        .group_by(Order.supplier_id)
    )
    exposure_map: dict[str, float] = {
        sid: float(total or 0) for sid, total in exposure_result.all()
    }

    scored = []
    for s in suppliers:
        regional_risks = risk_counts.get(s.region, 0)
        exposure = exposure_map.get(s.id, 0.0)
        reliability = float(s.reliability_score)

        risk_reliability = 1.0 - reliability
        risk_events = min(regional_risks / 5.0, 1.0)
        risk_exposure = min(exposure / 500_000.0, 1.0)

        composite = 0.40 * risk_reliability + 0.30 * risk_events + 0.30 * risk_exposure

        scored.append({
            "supplier_id": s.id,
            "supplier_name": s.name,
            "country": s.country,
            "region": s.region,
            "reliability_score": reliability,
            "regional_risk_events": regional_risks,
            "order_exposure_usd": round(exposure, 2),
            "composite_risk_score": round(composite, 4),
            "risk_tier": (
                "critical" if composite > 0.7
                else "high" if composite > 0.5
                else "medium" if composite > 0.3
                else "low"
            ),
        })

    scored.sort(key=lambda x: x["composite_risk_score"], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Rule-based triage
# ---------------------------------------------------------------------------


async def _get_new_events(db: AsyncSession) -> list[RiskEvent]:
    """Fetch risk events created in the last ingestion window."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=NEW_EVENT_WINDOW_MINUTES
    )
    result = await db.execute(
        select(RiskEvent)
        .where(RiskEvent.created_at >= cutoff)
        .where(RiskEvent.is_active.is_(True))
        .order_by(RiskEvent.severity_score.desc())
    )
    return list(result.scalars().all())


async def _check_regional_escalation(db: AsyncSession) -> list[dict]:
    """Detect regions with dangerous concentrations of active risk events."""
    result = await db.execute(
        select(RiskEvent.affected_region, func.count(RiskEvent.id))
        .where(RiskEvent.is_active.is_(True))
        .where(RiskEvent.severity.in_(["high", "critical"]))
        .group_by(RiskEvent.affected_region)
    )

    escalations = []
    for region, count in result.all():
        if region and count >= REGIONAL_ESCALATION_THRESHOLD:
            escalations.append({"region": region, "active_high_critical": count})
    return escalations


async def _create_auto_alert(
    db: AsyncSession,
    title: str,
    description: str,
    severity: str,
    severity_score: float,
    region: str | None,
) -> RiskEvent:
    """Create a system-generated risk alert."""
    event = RiskEvent(
        id=str(uuid.uuid4()),
        event_type="agent_alert",
        title=title,
        description=description,
        severity=severity,
        severity_score=severity_score,
        affected_region=region,
        started_at=datetime.utcnow(),
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    return event


async def run_triage(db: AsyncSession, new_event_count: int) -> dict:
    """Rule-based triage of the current risk landscape.

    Called automatically after each ingestion cycle. Returns a summary
    dict describing what was found and what actions were taken.
    """
    from app.routers.stream import publish_event

    summary = {
        "new_events_ingested": new_event_count,
        "suppliers_at_risk": [],
        "regional_escalations": [],
        "alerts_created": 0,
    }

    if new_event_count == 0:
        logger.info("Risk triage: no new events, skipping analysis")
        return summary

    # 1. Re-score all suppliers against current risk landscape
    scores = await _score_suppliers(db)
    at_risk = [s for s in scores if s["composite_risk_score"] >= SUPPLIER_RISK_ALERT_THRESHOLD]
    summary["suppliers_at_risk"] = at_risk

    # Broadcast supplier risk scores to dashboard
    if at_risk:
        await publish_event("supply_alert", {
            "severity": "high",
            "message": (
                f"{len(at_risk)} supplier(s) above risk threshold: "
                + ", ".join(s["supplier_name"] for s in at_risk[:5])
            ),
            "suppliers": at_risk[:10],
        })

    # 2. Check for regional escalation
    escalations = await _check_regional_escalation(db)
    summary["regional_escalations"] = escalations

    for esc in escalations:
        # Check if we already have a regional escalation alert active
        existing = await db.execute(
            select(RiskEvent.id)
            .where(RiskEvent.event_type == "agent_alert")
            .where(RiskEvent.is_active.is_(True))
            .where(RiskEvent.title.contains(f"Regional escalation — {esc['region']}"))
        )
        if existing.scalar_one_or_none():
            continue

        alert = await _create_auto_alert(
            db,
            title=f"Regional escalation — {esc['region']}",
            description=(
                f"Automated risk triage detected {esc['active_high_critical']} active "
                f"high/critical risk events in {esc['region']}. This concentration suggests "
                f"systemic regional disruption. Suppliers in this region may face cascading "
                f"delays. Consider activating contingency routes."
            ),
            severity="critical" if esc["active_high_critical"] >= 5 else "high",
            severity_score=min(0.5 + esc["active_high_critical"] * 0.1, 1.0),
            region=esc["region"],
        )
        summary["alerts_created"] += 1

        await publish_event("risk_update", {
            "id": alert.id,
            "title": alert.title,
            "severity": alert.severity,
            "severity_score": alert.severity_score,
            "event_type": "agent_alert",
            "affected_region": esc["region"],
            "description": alert.description,
        })

    # 3. Get newly ingested events and flag any critical ones
    new_events = await _get_new_events(db)
    critical_new = [e for e in new_events if e.severity in ("critical", "high")]

    if critical_new:
        await publish_event("agent_action", {
            "action": (
                f"Risk triage: {len(critical_new)} high/critical event(s) detected — "
                + ", ".join(e.title[:60] for e in critical_new[:3])
            ),
            "agent_type": "risk_monitor",
            "decision_type": "automated_triage",
            "event_count": len(critical_new),
        })

    if summary["alerts_created"] > 0:
        await db.commit()

    logger.info(
        "Risk triage complete: %d new events, %d suppliers at risk, "
        "%d regional escalations, %d alerts created",
        new_event_count,
        len(at_risk),
        len(escalations),
        summary["alerts_created"],
    )
    return summary


# ---------------------------------------------------------------------------
# Optional: Claude agent deep analysis
# ---------------------------------------------------------------------------


async def run_agent_analysis(db: AsyncSession, triage_summary: dict) -> str | None:
    """Invoke the Risk Monitor agent for deeper analysis of concerning signals.

    Only runs when there are high-risk suppliers or regional escalations.
    Returns the agent's text response, or None if analysis was skipped.
    """
    if (
        not triage_summary.get("suppliers_at_risk")
        and not triage_summary.get("regional_escalations")
    ):
        return None

    try:
        import anthropic

        anthropic.AsyncAnthropic()  # Verify API key is available
    except Exception:
        logger.info("Agent analysis skipped: Anthropic API key not configured")
        return None

    from app.agents.risk_monitor import run_risk_monitor
    from app.routers.stream import publish_event

    # Build a focused prompt from triage findings
    parts = [
        "AUTOMATED TRIAGE REPORT — analyze these findings and provide recommendations:\n"
    ]

    if triage_summary["suppliers_at_risk"]:
        parts.append(
            f"\n## Suppliers Above Risk Threshold ({len(triage_summary['suppliers_at_risk'])})"
        )
        for s in triage_summary["suppliers_at_risk"][:5]:
            parts.append(
                f"- {s['supplier_name']} ({s['country']}): "
                f"composite={s['composite_risk_score']:.2f}, "
                f"tier={s['risk_tier']}, "
                f"regional_events={s['regional_risk_events']}, "
                f"exposure=${s['order_exposure_usd']:,.0f}"
            )

    if triage_summary["regional_escalations"]:
        parts.append(
            f"\n## Regional Escalations ({len(triage_summary['regional_escalations'])})"
        )
        for esc in triage_summary["regional_escalations"]:
            parts.append(
                f"- {esc['region']}: {esc['active_high_critical']} active high/critical events"
            )

    parts.append(
        "\nUse your tools to fetch current risk events and supplier scores. "
        "Identify the top 3 actions the operations team should take right now. "
        "Create alerts for any emerging threats you identify that aren't already tracked."
    )

    prompt = "\n".join(parts)

    try:
        result = await run_risk_monitor(db, prompt)
        response_text = result.get("response", "")

        await publish_event("agent_action", {
            "action": "Risk Monitor completed deep analysis of current threat landscape",
            "agent_type": "risk_monitor",
            "decision_type": "deep_analysis",
            "summary": response_text[:300],
        })

        logger.info("Agent analysis complete: %d chars", len(response_text))
        return response_text

    except Exception:
        logger.exception("Agent analysis failed")
        return None
