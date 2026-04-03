"""Tool implementations for the Risk Monitor agent.

Each function accepts an AsyncSession and returns a JSON string suitable
for inclusion in an Anthropic tool_result message.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DemandSignal,
    Order,
    RiskEvent,
    RiskEventImpact,
    Supplier,
)


async def query_risk_events(
    db: AsyncSession,
    active_only: bool = True,
    severity: str | None = None,
    region: str | None = None,
) -> str:
    """Retrieve risk events, optionally filtered by status, severity, or region."""
    stmt = select(RiskEvent).order_by(RiskEvent.started_at.desc())

    if active_only:
        stmt = stmt.where(RiskEvent.is_active.is_(True))
    if severity:
        stmt = stmt.where(RiskEvent.severity == severity)
    if region:
        stmt = stmt.where(RiskEvent.affected_region == region)

    result = await db.execute(stmt)
    events = result.scalars().all()

    return json.dumps(
        [
            {
                "id": e.id,
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "severity": e.severity,
                "severity_score": float(e.severity_score),
                "affected_region": e.affected_region,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "expected_end": e.expected_end.isoformat() if e.expected_end else None,
                "is_active": e.is_active,
            }
            for e in events
        ],
        default=str,
    )


async def score_suppliers(
    db: AsyncSession,
    region: str | None = None,
) -> str:
    """Compute composite risk scores for suppliers.

    Score combines: base reliability, count of active risk events affecting
    their region, and total value of in-flight orders (exposure).
    """
    stmt = select(Supplier).where(Supplier.is_active.is_(True))
    if region:
        stmt = stmt.where(Supplier.region == region)
    result = await db.execute(stmt)
    suppliers = result.scalars().all()

    # Active risk events by region
    risk_stmt = (
        select(RiskEvent.affected_region, func.count(RiskEvent.id))
        .where(RiskEvent.is_active.is_(True))
        .group_by(RiskEvent.affected_region)
    )
    risk_result = await db.execute(risk_stmt)
    risk_counts: dict[str | None, int] = dict(risk_result.all())

    # Order exposure by supplier (in-flight orders)
    exposure_stmt = (
        select(Order.supplier_id, func.sum(Order.total_cost))
        .where(Order.status.in_(["pending", "in_transit", "processing"]))
        .group_by(Order.supplier_id)
    )
    exposure_result = await db.execute(exposure_stmt)
    exposure_map: dict[str, float] = {
        sid: float(total or 0) for sid, total in exposure_result.all()
    }

    scored = []
    for s in suppliers:
        regional_risk_count = risk_counts.get(s.region, 0)
        order_exposure = exposure_map.get(s.id, 0.0)
        reliability = float(s.reliability_score)

        # Composite risk score: lower is better (0 = no risk, 1 = extreme)
        # Weighted: 40% inverse reliability, 30% regional risk, 30% exposure-based
        risk_from_reliability = 1.0 - reliability
        risk_from_events = min(regional_risk_count / 5.0, 1.0)
        risk_from_exposure = min(order_exposure / 500_000.0, 1.0)

        composite = (
            0.40 * risk_from_reliability
            + 0.30 * risk_from_events
            + 0.30 * risk_from_exposure
        )

        scored.append(
            {
                "supplier_id": s.id,
                "supplier_name": s.name,
                "country": s.country,
                "region": s.region,
                "reliability_score": reliability,
                "regional_risk_events": regional_risk_count,
                "order_exposure_usd": round(order_exposure, 2),
                "composite_risk_score": round(composite, 4),
                "risk_tier": (
                    "critical" if composite > 0.7
                    else "high" if composite > 0.5
                    else "medium" if composite > 0.3
                    else "low"
                ),
            }
        )

    scored.sort(key=lambda x: x["composite_risk_score"], reverse=True)
    return json.dumps(scored, default=str)


async def fetch_risk_signals(db: AsyncSession) -> str:
    """Aggregate recent risk events and demand anomalies into a signals feed.

    Signals are inputs the Risk Monitor uses to detect emerging threats.
    """
    # Recent risk events (last 30 active or recently created)
    events_stmt = (
        select(RiskEvent)
        .order_by(RiskEvent.created_at.desc())
        .limit(20)
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    # Demand anomalies: signals where actual deviates from forecast by >20%
    anomaly_stmt = (
        select(DemandSignal)
        .where(DemandSignal.actual_qty.isnot(None))
        .where(
            func.abs(DemandSignal.variance_pct) > 20.0
        )
        .order_by(DemandSignal.signal_date.desc())
        .limit(20)
    )
    anomaly_result = await db.execute(anomaly_stmt)
    anomalies = anomaly_result.scalars().all()

    signals = []

    for e in events:
        signals.append(
            {
                "signal_type": "risk_event",
                "id": e.id,
                "title": e.title,
                "severity": e.severity,
                "severity_score": float(e.severity_score),
                "region": e.affected_region,
                "event_type": e.event_type,
                "is_active": e.is_active,
                "started_at": e.started_at.isoformat() if e.started_at else None,
            }
        )

    for a in anomalies:
        signals.append(
            {
                "signal_type": "demand_anomaly",
                "product_id": a.product_id,
                "region": a.region,
                "signal_date": a.signal_date.isoformat() if a.signal_date else None,
                "forecast_qty": a.forecast_qty,
                "actual_qty": a.actual_qty,
                "variance_pct": float(a.variance_pct) if a.variance_pct else None,
            }
        )

    return json.dumps(signals, default=str)


async def create_alert(
    db: AsyncSession,
    title: str,
    description: str,
    severity: str,
    severity_score: float,
    affected_region: str | None = None,
    event_type: str = "agent_alert",
) -> str:
    """Create a new risk event / alert in the database."""
    event = RiskEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        title=title,
        description=description,
        severity=severity,
        severity_score=severity_score,
        affected_region=affected_region,
        started_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    return json.dumps(
        {
            "status": "created",
            "alert_id": event.id,
            "title": event.title,
            "severity": event.severity,
        }
    )
