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


class TicketApproveRequest(BaseModel):
    """Operator approval payload with optional edits before outbound routing."""

    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    assigned_team: str | None = Field(default=None, max_length=64)
    draft_reply: str | None = Field(default=None, max_length=20000)


class TicketAnalysisResponse(BaseModel):
    """Serialized LLM + RAG triage analysis record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    provider: str
    model: str
    category: TicketCategory
    priority: TicketPriority
    assigned_team: str
    summary: str
    draft_reply: str
    confidence: float
    needs_human_review: bool
    reasoning: str
    cited_kb_ids: list[str]
    injection_detected: bool
    injection_risk_score: float
    injection_patterns: list[str]
    repair_attempts: int
    fallback_used: bool
    latency_ms: float
    created_at: datetime


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
    analyses: list[TicketAnalysisResponse] = Field(default_factory=list)


class TicketListResponse(BaseModel):
    """Paginated ticket listing response."""

    items: list[TicketResponse]
    total: int
    limit: int
    offset: int


class DashboardMetricsResponse(BaseModel):
    """Aggregated operational and AI quality metrics for the operator dashboard."""

    total_tickets: int
    tickets_by_status: dict[str, int]
    tickets_by_category: dict[str, int]
    tickets_by_priority: dict[str, int]
    total_analyses: int
    avg_confidence: float
    avg_latency_ms: float
    human_review_rate: float
    injection_detected_count: int
    total_repair_attempts: int
    total_deliveries: int
    deliveries_by_status: dict[str, int]
    deliveries_by_target: dict[str, int]
