from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductBrief
from app.schemas.route import ShippingRouteBrief
from app.schemas.supplier import SupplierBrief


class OrderBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_number: str
    status: str
    total_cost: float
    ordered_at: datetime
    expected_delivery: datetime | None
    delay_days: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_number: str
    product_id: str
    supplier_id: str
    route_id: str | None
    quantity: int
    unit_price: float
    total_cost: float
    status: str
    ordered_at: datetime
    expected_delivery: datetime | None
    actual_delivery: datetime | None
    delay_days: int
    delay_reason: str | None
    created_at: datetime
    updated_at: datetime

    supplier: SupplierBrief
    product: ProductBrief
    route: ShippingRouteBrief | None
