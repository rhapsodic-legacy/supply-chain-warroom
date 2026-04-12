import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlertRule(Base):
    """User-defined alerting rule that triggers agent analysis when conditions are met.

    Each rule monitors a specific metric (e.g. supplier reliability, risk event count)
    with an operator and threshold. When the condition is met, the system creates a
    risk alert and optionally triggers agent analysis.
    """

    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # What to monitor
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    # "supplier_reliability", "risk_event_count", "order_delay_days",
    # "composite_risk_score", "regional_risk_density"

    # Condition
    operator: Mapped[str] = mapped_column(String(5), nullable=False)
    # "lt" (<), "lte" (<=), "gt" (>), "gte" (>=), "eq" (==)
    threshold: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    # Optional filters to narrow the scope
    filter_region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filter_supplier_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    filter_severity: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # What happens when it fires
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="high")
    trigger_agent_analysis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # State tracking
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trigger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
