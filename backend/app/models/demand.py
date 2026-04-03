import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DemandSignal(Base):
    __tablename__ = "demand_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False
    )
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    variance_pct: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
