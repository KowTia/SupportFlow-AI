"""Ticket and delivery log ORM models."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis import TicketAnalysis


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """Return string values for non-native SQLAlchemy Enum columns."""
    return [member.value for member in enum_cls]


class TicketStatus(StrEnum):
    """Lifecycle states for an inbound support ticket."""

    NEW = "new"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    ROUTED = "routed"
    FAILED = "failed"


class TicketPriority(StrEnum):
    """Triage priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(StrEnum):
    """Normalized support ticket categories."""

    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature_request"
    SECURITY = "security"
    OTHER = "other"


class DeliveryTarget(StrEnum):
    """Supported outbound integration targets."""

    WEBHOOK = "webhook"
    GOOGLE_SHEETS = "google_sheets"


class DeliveryStatus(StrEnum):
    """Status of an outbound delivery attempt."""

    PENDING = "pending"
    SUCCESS = "success"
    DRY_RUN = "dry_run"
    FAILED = "failed"


class Ticket(Base):
    """Inbound customer support ticket with triage metadata."""

    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), default="api", nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(
            TicketStatus,
            native_enum=False,
            create_constraint=False,
            length=32,
            values_callable=_enum_values,
        ),
        default=TicketStatus.NEW,
        index=True,
        nullable=False,
    )
    category: Mapped[TicketCategory | None] = mapped_column(
        Enum(
            TicketCategory,
            native_enum=False,
            create_constraint=False,
            length=64,
            values_callable=_enum_values,
        ),
        index=True,
        nullable=True,
    )
    priority: Mapped[TicketPriority | None] = mapped_column(
        Enum(
            TicketPriority,
            native_enum=False,
            create_constraint=False,
            length=32,
            values_callable=_enum_values,
        ),
        index=True,
        nullable=True,
    )
    assigned_team: Mapped[str | None] = mapped_column(String(64), nullable=True)
    draft_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    delivery_logs: Mapped[list["DeliveryLog"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    analyses: Mapped[list["TicketAnalysis"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TicketAnalysis.created_at.desc()",
    )


class DeliveryLog(Base):
    """Audit log for outbound webhook and spreadsheet deliveries."""

    __tablename__ = "delivery_logs"

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
    target: Mapped[DeliveryTarget] = mapped_column(
        Enum(
            DeliveryTarget,
            native_enum=False,
            create_constraint=False,
            length=64,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(
            DeliveryStatus,
            native_enum=False,
            create_constraint=False,
            length=32,
            values_callable=_enum_values,
        ),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    ticket: Mapped[Ticket] = relationship(back_populates="delivery_logs")
