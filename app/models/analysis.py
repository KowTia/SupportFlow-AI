"""ORM model for persisted LLM triage analyses."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.ticket import TicketCategory, TicketPriority, _enum_values

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class TicketAnalysis(Base):
    """Audit record of an LLM + RAG triage analysis run for a ticket."""

    __tablename__ = "ticket_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[TicketCategory] = mapped_column(
        Enum(
            TicketCategory,
            native_enum=False,
            create_constraint=False,
            length=64,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(
            TicketPriority,
            native_enum=False,
            create_constraint=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    assigned_team: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    draft_reply: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    cited_kb_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    injection_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    injection_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    injection_patterns: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    repair_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="analyses")
