from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RiskEventImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    risk_event_id: str
    entity_type: str
    entity_id: str | None
    entity_name: str
    impact_multiplier: float
    created_at: datetime


class RiskEventCreate(BaseModel):
    event_type: str
    title: str
    description: str
    severity: str
    severity_score: float
    affected_region: str | None = None
    expected_end: datetime | None = None


class RiskEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    title: str
    description: str
    severity: str
    severity_score: float
    affected_region: str | None
    started_at: datetime
    expected_end: datetime | None
    actual_end: datetime | None
    is_active: bool
    created_at: datetime

    impacts: list[RiskEventImpactResponse]
