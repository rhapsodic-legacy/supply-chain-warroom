import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    trigger_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("risk_events.id"), nullable=True
    )
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    affected_orders: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    parameters: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_impact: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    time_impact_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
