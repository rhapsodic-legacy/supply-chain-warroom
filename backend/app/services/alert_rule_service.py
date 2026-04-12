"""Alert rule service — CRUD, evaluation, and triggering.

Evaluates user-defined rules against current supply chain state and fires
alerts + agent analysis when conditions are met.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertRule, Order, RiskEvent, Supplier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_rule(
    db: AsyncSession,
    *,
    name: str,
    metric: str,
    operator: str,
    threshold: float,
    description: str | None = None,
    filter_region: str | None = None,
    filter_supplier_id: str | None = None,
    filter_severity: str | None = None,
    severity: str = "high",
    trigger_agent_analysis: bool = True,
    cooldown_minutes: int = 60,
) -> AlertRule:
    rule = AlertRule(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        metric=metric,
        operator=operator,
        threshold=threshold,
        filter_region=filter_region,
        filter_supplier_id=filter_supplier_id,
        filter_severity=filter_severity,
        severity=severity,
        trigger_agent_analysis=trigger_agent_analysis,
        cooldown_minutes=cooldown_minutes,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def list_rules(
    db: AsyncSession,
    enabled_only: bool = False,
    limit: int = 100,
) -> list[AlertRule]:
    stmt = select(AlertRule).order_by(AlertRule.created_at.desc()).limit(limit)
    if enabled_only:
        stmt = stmt.where(AlertRule.is_enabled.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_rule(db: AsyncSession, rule_id: str) -> AlertRule | None:
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    return result.scalar_one_or_none()


async def update_rule(
    db: AsyncSession,
    rule_id: str,
    **kwargs,
) -> AlertRule | None:
    rule = await get_rule(db, rule_id)
    if not rule:
        return None
    for key, value in kwargs.items():
        if hasattr(rule, key) and value is not None:
            setattr(rule, key, value)
    rule.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(rule)
    return rule


async def delete_rule(db: AsyncSession, rule_id: str) -> bool:
    rule = await get_rule(db, rule_id)
    if not rule:
        return False
    await db.delete(rule)
    await db.flush()
    return True


async def toggle_rule(db: AsyncSession, rule_id: str) -> AlertRule | None:
    rule = await get_rule(db, rule_id)
    if not rule:
        return None
    rule.is_enabled = not rule.is_enabled
    rule.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

_OPERATORS = {
    "lt": lambda val, thresh: val < thresh,
    "lte": lambda val, thresh: val <= thresh,
    "gt": lambda val, thresh: val > thresh,
    "gte": lambda val, thresh: val >= thresh,
    "eq": lambda val, thresh: val == thresh,
}

_OPERATOR_LABELS = {
    "lt": "below",
    "lte": "at or below",
    "gt": "above",
    "gte": "at or above",
    "eq": "exactly",
}


# ---------------------------------------------------------------------------
# Metric evaluators
# ---------------------------------------------------------------------------


async def _eval_supplier_reliability(
    db: AsyncSession,
    rule: AlertRule,
) -> list[dict]:
    """Check if any supplier's reliability_score crosses the threshold."""
    stmt = select(Supplier).where(Supplier.is_active.is_(True))
    if rule.filter_region:
        stmt = stmt.where(Supplier.region == rule.filter_region)
    if rule.filter_supplier_id:
        stmt = stmt.where(Supplier.id == rule.filter_supplier_id)

    result = await db.execute(stmt)
    suppliers = result.scalars().all()

    op_fn = _OPERATORS.get(rule.operator, _OPERATORS["lt"])
    threshold = float(rule.threshold)

    violations = []
    for s in suppliers:
        score = float(s.reliability_score)
        if op_fn(score, threshold):
            violations.append({
                "entity": s.name,
                "entity_id": s.id,
                "metric_value": score,
                "region": s.region,
            })
    return violations


async def _eval_risk_event_count(
    db: AsyncSession,
    rule: AlertRule,
) -> list[dict]:
    """Check if the count of active risk events crosses the threshold."""
    stmt = select(func.count(RiskEvent.id)).where(RiskEvent.is_active.is_(True))
    if rule.filter_region:
        stmt = stmt.where(RiskEvent.affected_region == rule.filter_region)
    if rule.filter_severity:
        stmt = stmt.where(RiskEvent.severity == rule.filter_severity)

    result = await db.execute(stmt)
    count = result.scalar() or 0

    op_fn = _OPERATORS.get(rule.operator, _OPERATORS["gt"])
    threshold = float(rule.threshold)

    if op_fn(count, threshold):
        region_label = rule.filter_region or "all regions"
        return [{
            "entity": f"Risk events in {region_label}",
            "entity_id": None,
            "metric_value": count,
            "region": rule.filter_region,
        }]
    return []


async def _eval_order_delay_days(
    db: AsyncSession,
    rule: AlertRule,
) -> list[dict]:
    """Check if any order's delay_days crosses the threshold."""
    stmt = select(Order).where(Order.status.in_(["pending", "in_transit", "processing"]))
    if rule.filter_supplier_id:
        stmt = stmt.where(Order.supplier_id == rule.filter_supplier_id)

    result = await db.execute(stmt)
    orders = result.scalars().all()

    op_fn = _OPERATORS.get(rule.operator, _OPERATORS["gt"])
    threshold = float(rule.threshold)

    violations = []
    for o in orders:
        if op_fn(o.delay_days, threshold):
            violations.append({
                "entity": o.order_number,
                "entity_id": o.id,
                "metric_value": o.delay_days,
                "region": None,
            })
    return violations


async def _eval_composite_risk_score(
    db: AsyncSession,
    rule: AlertRule,
) -> list[dict]:
    """Check if any supplier's composite risk score crosses the threshold.

    Uses the same scoring logic as risk_analysis._score_suppliers.
    """
    stmt = select(Supplier).where(Supplier.is_active.is_(True))
    if rule.filter_region:
        stmt = stmt.where(Supplier.region == rule.filter_region)
    if rule.filter_supplier_id:
        stmt = stmt.where(Supplier.id == rule.filter_supplier_id)

    result = await db.execute(stmt)
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

    op_fn = _OPERATORS.get(rule.operator, _OPERATORS["gt"])
    threshold = float(rule.threshold)

    violations = []
    for s in suppliers:
        regional_risks = risk_counts.get(s.region, 0)
        exposure = exposure_map.get(s.id, 0.0)
        reliability = float(s.reliability_score)

        composite = (
            0.40 * (1.0 - reliability)
            + 0.30 * min(regional_risks / 5.0, 1.0)
            + 0.30 * min(exposure / 500_000.0, 1.0)
        )

        if op_fn(round(composite, 4), threshold):
            violations.append({
                "entity": s.name,
                "entity_id": s.id,
                "metric_value": round(composite, 4),
                "region": s.region,
            })
    return violations


async def _eval_regional_risk_density(
    db: AsyncSession,
    rule: AlertRule,
) -> list[dict]:
    """Check if any region has risk event density above the threshold."""
    stmt = (
        select(RiskEvent.affected_region, func.count(RiskEvent.id).label("count"))
        .where(RiskEvent.is_active.is_(True))
        .group_by(RiskEvent.affected_region)
    )
    if rule.filter_severity:
        stmt = stmt.where(RiskEvent.severity == rule.filter_severity)

    result = await db.execute(stmt)

    op_fn = _OPERATORS.get(rule.operator, _OPERATORS["gte"])
    threshold = float(rule.threshold)

    violations = []
    for region, count in result.all():
        if region and op_fn(count, threshold):
            violations.append({
                "entity": f"Region: {region}",
                "entity_id": None,
                "metric_value": count,
                "region": region,
            })
    return violations


_METRIC_EVALUATORS = {
    "supplier_reliability": _eval_supplier_reliability,
    "risk_event_count": _eval_risk_event_count,
    "order_delay_days": _eval_order_delay_days,
    "composite_risk_score": _eval_composite_risk_score,
    "regional_risk_density": _eval_regional_risk_density,
}


# ---------------------------------------------------------------------------
# Rule evaluation engine
# ---------------------------------------------------------------------------


async def evaluate_rule(db: AsyncSession, rule: AlertRule) -> list[dict]:
    """Evaluate a single rule against current state.

    Returns a list of violations (empty if no condition is met).
    """
    evaluator = _METRIC_EVALUATORS.get(rule.metric)
    if not evaluator:
        logger.warning("Unknown metric '%s' for rule '%s'", rule.metric, rule.name)
        return []

    return await evaluator(db, rule)


async def evaluate_all_rules(db: AsyncSession) -> dict:
    """Evaluate all enabled rules and fire alerts for violations.

    Returns a summary of what was evaluated and triggered.
    """
    from app.routers.stream import publish_event

    rules = await list_rules(db, enabled_only=True)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    summary = {
        "rules_evaluated": len(rules),
        "rules_triggered": 0,
        "alerts_created": 0,
        "agent_analyses_triggered": 0,
        "triggered_rules": [],
    }

    for rule in rules:
        # Check cooldown
        if rule.last_triggered_at:
            cooldown_end = rule.last_triggered_at + timedelta(minutes=rule.cooldown_minutes)
            if now < cooldown_end:
                continue

        violations = await evaluate_rule(db, rule)
        if not violations:
            continue

        # Rule triggered!
        summary["rules_triggered"] += 1
        op_label = _OPERATOR_LABELS.get(rule.operator, rule.operator)

        # Update rule state
        rule.last_triggered_at = now
        rule.trigger_count += 1
        await db.flush()

        # Build violation description
        violation_names = [v["entity"] for v in violations[:5]]
        violation_desc = ", ".join(violation_names)
        if len(violations) > 5:
            violation_desc += f" (+{len(violations) - 5} more)"

        alert_title = f"Alert rule triggered: {rule.name}"
        alert_description = (
            f"Rule '{rule.name}' fired: {rule.metric} is {op_label} {float(rule.threshold)} "
            f"for {len(violations)} entit{'y' if len(violations) == 1 else 'ies'}.\n\n"
            f"Affected: {violation_desc}\n\n"
            f"Values: {', '.join(f'{v['entity']}={v['metric_value']}' for v in violations[:5])}"
        )

        # Create a risk alert
        alert = RiskEvent(
            id=str(uuid.uuid4()),
            event_type="rule_alert",
            title=alert_title,
            description=alert_description,
            severity=rule.severity,
            severity_score=min(0.5 + len(violations) * 0.1, 1.0),
            affected_region=violations[0].get("region") if violations else None,
            started_at=now,
            is_active=True,
            created_at=now,
        )
        db.add(alert)
        summary["alerts_created"] += 1

        await publish_event(
            "risk_update",
            {
                "id": alert.id,
                "title": alert.title,
                "severity": alert.severity,
                "severity_score": alert.severity_score,
                "event_type": "rule_alert",
                "affected_region": alert.affected_region,
                "description": alert.description,
                "rule_id": rule.id,
                "rule_name": rule.name,
            },
        )

        triggered_info = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "metric": rule.metric,
            "violations": len(violations),
            "alert_id": alert.id,
        }

        # Optionally trigger agent analysis
        if rule.trigger_agent_analysis:
            summary["agent_analyses_triggered"] += 1
            triggered_info["agent_analysis"] = True

            await publish_event(
                "agent_action",
                {
                    "action": (
                        f"Alert rule '{rule.name}' triggered agent analysis: "
                        f"{rule.metric} {op_label} {float(rule.threshold)}"
                    ),
                    "agent_type": "risk_monitor",
                    "decision_type": "rule_triggered_analysis",
                    "rule_id": rule.id,
                    "violations": len(violations),
                },
            )

        summary["triggered_rules"].append(triggered_info)

    if summary["alerts_created"] > 0:
        await db.commit()

    logger.info(
        "Alert rules evaluated: %d rules, %d triggered, %d alerts created",
        summary["rules_evaluated"],
        summary["rules_triggered"],
        summary["alerts_created"],
    )
    return summary
