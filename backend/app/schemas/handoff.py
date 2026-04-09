from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentHandoffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    sequence: int
    from_agent: str
    to_agent: str
    query: str
    status: str
    result_summary: str | None
    duration_ms: int | None
    started_at: datetime
    completed_at: datetime | None


class AgentHandoffSessionResponse(BaseModel):
    """All handoffs from a single orchestrator session, grouped for pipeline display."""

    session_id: str
    handoffs: list[AgentHandoffResponse]
    started_at: datetime
    completed_at: datetime | None
    total_duration_ms: int | None
