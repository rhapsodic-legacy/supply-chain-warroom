from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShippingRouteBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    origin_port: str
    destination_port: str
    transport_mode: str
    base_transit_days: int
    risk_score: float


class ShippingRouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    origin_port: str
    origin_country: str
    destination_port: str
    destination_country: str
    transport_mode: str
    base_transit_days: int
    transit_variance_days: int
    cost_per_kg: float
    risk_score: float
    capacity_tons: int
    is_active: bool
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    created_at: datetime
