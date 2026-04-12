"""Generate seed alert rules — sensible defaults for a supply chain war room."""

from __future__ import annotations

import random
import uuid
from datetime import datetime


def generate_alert_rules(seed: int = 42) -> list[dict]:
    """Generate a set of realistic default alert rules."""
    rng = random.Random(seed)
    now = datetime(2026, 3, 30, 12, 0, 0)

    rules: list[dict] = []

    def _add(
        *,
        name: str,
        description: str,
        metric: str,
        operator: str,
        threshold: float,
        severity: str = "high",
        trigger_agent_analysis: bool = True,
        filter_region: str | None = None,
        filter_supplier_id: str | None = None,
        filter_severity: str | None = None,
        cooldown_minutes: int = 60,
        trigger_count: int = 0,
        last_triggered_at: str | None = None,
    ) -> None:
        rules.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "name": name,
                "description": description,
                "metric": metric,
                "operator": operator,
                "threshold": threshold,
                "filter_region": filter_region,
                "filter_supplier_id": filter_supplier_id,
                "filter_severity": filter_severity,
                "severity": severity,
                "trigger_agent_analysis": trigger_agent_analysis,
                "is_enabled": True,
                "last_triggered_at": last_triggered_at,
                "trigger_count": trigger_count,
                "cooldown_minutes": cooldown_minutes,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        )

    _add(
        name="Supplier reliability below 0.7",
        description=(
            "Alert when any supplier's reliability score drops below 0.7. "
            "This indicates the supplier is consistently underperforming and "
            "may need corrective action or replacement."
        ),
        metric="supplier_reliability",
        operator="lt",
        threshold=0.70,
        severity="high",
        cooldown_minutes=120,
        trigger_count=2,
        last_triggered_at=(now - __import__("datetime").timedelta(hours=3)).isoformat(),
    )

    _add(
        name="Critical risk events exceed 3",
        description=(
            "Alert when the number of active critical risk events exceeds 3. "
            "Multiple simultaneous critical events suggest systemic disruption."
        ),
        metric="risk_event_count",
        operator="gt",
        threshold=3.0,
        filter_severity="critical",
        severity="critical",
        trigger_agent_analysis=True,
        cooldown_minutes=60,
    )

    _add(
        name="East Asia risk density",
        description=(
            "Alert when East Asia has 2 or more active risk events. "
            "Given our heavy supplier concentration in this region, even "
            "moderate clustering warrants immediate attention."
        ),
        metric="regional_risk_density",
        operator="gte",
        threshold=2.0,
        filter_region=None,  # Checks all regions, not just East Asia
        severity="high",
        cooldown_minutes=90,
        trigger_count=1,
        last_triggered_at=(now - __import__("datetime").timedelta(hours=6)).isoformat(),
    )

    _add(
        name="Order delay exceeds 7 days",
        description=(
            "Alert when any active order has accumulated more than 7 days of delay. "
            "Extended delays risk stockouts and customer SLA breaches."
        ),
        metric="order_delay_days",
        operator="gt",
        threshold=7.0,
        severity="medium",
        trigger_agent_analysis=False,
        cooldown_minutes=180,
    )

    _add(
        name="Composite risk score above 0.6",
        description=(
            "Alert when any supplier's composite risk score (blending reliability, "
            "regional threats, and financial exposure) exceeds 0.6. This is an "
            "early warning before suppliers reach critical risk levels."
        ),
        metric="composite_risk_score",
        operator="gt",
        threshold=0.60,
        severity="high",
        cooldown_minutes=120,
    )

    return rules
