"""Pydantic v2 schemas for support tickets and delivery logs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.ticket import (
    DeliveryStatus,
    DeliveryTarget,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)


class TicketCreate(BaseModel):
    """Inbound payload for creating a support ticket."""

    subject: str = Field(min_length=3, max_length=500)
    body: str = Field(min_length=5, max_length=20000)
    source: str = Field(default="api", min_length=1, max_length=64)
    customer_email: EmailStr | None = None
    customer_name: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, min_length=4, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TicketUpdate(BaseModel):
    """Partial update payload for operator triage and review."""

    status: TicketStatus | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    assigned_team: str | None = Field(default=None, max_length=64)
    draft_reply: str | None = Field(default=None, max_length=20000)


class DeliveryLogResponse(BaseModel):
    """Serialized outbound delivery audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    target: DeliveryTarget
    endpoint: str | None
    status: DeliveryStatus
    status_code: int | None
    attempt: int
    request_payload: dict[str, Any] | None
    response_body: str | None
    error_message: str | None
    created_at: datetime


class TicketResponse(BaseModel):
    """Serialized support ticket representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    idempotency_key: str
    source: str
    customer_email: str | None
    customer_name: str | None
    subject: str
    body: str
    status: TicketStatus
    category: TicketCategory | None
    priority: TicketPriority | None
    assigned_team: str | None
    draft_reply: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    delivery_logs: list[DeliveryLogResponse] = Field(default_factory=list)


class TicketListResponse(BaseModel):
    """Paginated ticket listing response."""

    items: list[TicketResponse]
    total: int
    limit: int
    offset: int
