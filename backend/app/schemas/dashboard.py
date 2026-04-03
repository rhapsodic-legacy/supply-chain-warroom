from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DashboardOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_orders: int
    active_orders: int
    total_suppliers: int
    active_suppliers: int
    active_risk_events: int
    critical_risk_events: int
    avg_fill_rate: float
    total_revenue: float


class SupplyHealthItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    supplier_id: str
    supplier_name: str
    region: str
    reliability_score: float
    active_risk_count: int
    pending_orders: int


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    agent_actions: list[dict[str, Any]]
    timestamp: datetime
