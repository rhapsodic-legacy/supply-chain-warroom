from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentMemoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_type: str
    category: str
    affected_region: str | None
    severity: str | None
    outcome: str
    lesson: str
    occurrence_count: int
    created_at: datetime


class AgentMemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_type: str
    decision_id: str | None
    trigger_event_id: str | None
    category: str
    affected_region: str | None
    severity: str | None
    risk_type: str | None
    situation: str
    action_taken: str
    outcome: str
    lesson: str
    confidence_score: float
    cost_impact: float | None
    time_impact_days: int | None
    occurrence_count: int
    last_referenced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentMemoryStats(BaseModel):
    total_memories: int
    by_outcome: dict[str, int]
    by_category: dict[str, int]
    by_agent: dict[str, int]
