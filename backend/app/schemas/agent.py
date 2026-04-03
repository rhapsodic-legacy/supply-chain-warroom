from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentDecisionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_type: str
    decision_type: str
    decision_summary: str
    confidence_score: float
    status: str
    decided_at: datetime


class AgentDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_type: str
    trigger_event_id: str | None
    decision_type: str
    decision_summary: str
    reasoning: str
    confidence_score: float
    affected_orders: str
    parameters: str
    status: str
    outcome: str | None
    outcome_notes: str | None
    cost_impact: float | None
    time_impact_days: int | None
    decided_at: datetime
    executed_at: datetime | None
    created_at: datetime
