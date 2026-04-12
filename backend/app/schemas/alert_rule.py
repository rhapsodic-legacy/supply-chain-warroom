from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    metric: Literal[
        "supplier_reliability",
        "risk_event_count",
        "order_delay_days",
        "composite_risk_score",
        "regional_risk_density",
    ]
    operator: Literal["lt", "lte", "gt", "gte", "eq"]
    threshold: float
    filter_region: str | None = None
    filter_supplier_id: str | None = None
    filter_severity: str | None = None
    severity: Literal["low", "medium", "high", "critical"] = "high"
    trigger_agent_analysis: bool = True
    cooldown_minutes: int = Field(60, ge=1, le=1440)


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    metric: Literal[
        "supplier_reliability",
        "risk_event_count",
        "order_delay_days",
        "composite_risk_score",
        "regional_risk_density",
    ] | None = None
    operator: Literal["lt", "lte", "gt", "gte", "eq"] | None = None
    threshold: float | None = None
    filter_region: str | None = None
    filter_supplier_id: str | None = None
    filter_severity: str | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    trigger_agent_analysis: bool | None = None
    cooldown_minutes: int | None = None


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    metric: str
    operator: str
    threshold: float
    filter_region: str | None
    filter_supplier_id: str | None
    filter_severity: str | None
    severity: str
    trigger_agent_analysis: bool
    is_enabled: bool
    last_triggered_at: datetime | None
    trigger_count: int
    cooldown_minutes: int
    created_at: datetime
    updated_at: datetime


class AlertRuleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    metric: str
    operator: str
    threshold: float
    severity: str
    is_enabled: bool
    trigger_count: int
    last_triggered_at: datetime | None


class AlertRuleEvalSummary(BaseModel):
    rules_evaluated: int
    rules_triggered: int
    alerts_created: int
    agent_analyses_triggered: int
    triggered_rules: list[dict]
