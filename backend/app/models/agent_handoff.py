import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentHandoff(Base):
    __tablename__ = "agent_handoffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="Groups handoffs from a single chat turn",
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    from_agent: Mapped[str] = mapped_column(String(30), nullable=False)
    to_agent: Mapped[str] = mapped_column(String(30), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        doc="running | completed | error",
    )
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
