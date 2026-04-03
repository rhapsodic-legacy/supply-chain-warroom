from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SupplierCreate(BaseModel):
    name: str
    country: str
    region: str
    city: str
    reliability_score: float = 0.85
    base_lead_time_days: int
    lead_time_variance: int = 2
    cost_multiplier: float = 1.00
    capacity_units: int = 10000


class SupplierBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    country: str
    region: str
    reliability_score: float
    is_active: bool


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    country: str
    region: str
    city: str
    reliability_score: float
    base_lead_time_days: int
    lead_time_variance: int
    cost_multiplier: float
    capacity_units: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
