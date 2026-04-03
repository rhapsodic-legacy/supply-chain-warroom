import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ShippingRoute(Base):
    __tablename__ = "shipping_routes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    origin_port: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_country: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_port: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(100), nullable=False)
    transport_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    base_transit_days: Mapped[int] = mapped_column(Integer, nullable=False)
    transit_variance_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    cost_per_kg: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    risk_score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.10)
    capacity_tons: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    origin_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False, default=0.0)
    origin_lon: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False, default=0.0)
    dest_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False, default=0.0)
    dest_lon: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
