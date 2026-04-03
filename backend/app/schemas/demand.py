from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DemandSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    region: str
    signal_date: date
    forecast_qty: int
    actual_qty: int | None
    variance_pct: float | None
    created_at: datetime


class DemandSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    region: str
    total_forecast: int
    total_actual: int
    avg_variance_pct: float
