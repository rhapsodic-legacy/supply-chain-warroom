from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    category: str
    is_critical: bool


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    category: str
    unit_cost: float
    weight_kg: float
    is_critical: bool
    description: str | None
    created_at: datetime
