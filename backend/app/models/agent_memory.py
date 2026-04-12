import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentMemory(Base):
    """Stores learned patterns and lessons from past agent decisions.

    Each memory captures what happened, what the agent decided, and what the
    outcome was — enabling future agents to surface "last time this happened..."
    context and improve recommendations over time.
    """

    __tablename__ = "agent_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    decision_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_decisions.id"), nullable=True
    )
    trigger_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("risk_events.id"), nullable=True
    )

    # Classification fields for similarity matching
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "port_closure", "supplier_failure", "demand_spike", "weather_disruption"
    affected_region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    risk_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # The learned content
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    # "effective", "partially_effective", "ineffective", "pending"
    lesson: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.5)

    # Impact metrics from the original decision
    cost_impact: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    time_impact_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # How many times this pattern has been observed
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_referenced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
