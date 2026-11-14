"""Ticket ingestion and triage CRUD endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.ticket import TicketCategory, TicketPriority, TicketStatus
from app.schemas.ticket import TicketCreate, TicketListResponse, TicketResponse, TicketUpdate
from app.services.tickets import (
    create_ticket_idempotent,
    get_ticket_by_id,
    list_tickets,
    update_ticket,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(
    payload: TicketCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=4, max_length=128),
    ] = None,
) -> TicketResponse:
    """Create a support ticket with idempotency support via header, body, or content hash."""
    ticket, created = await create_ticket_idempotent(
        session,
        payload,
        header_key=idempotency_key,
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    response.headers["X-Idempotent-Replay"] = "false" if created else "true"
    return TicketResponse.model_validate(ticket)


@router.get("", response_model=TicketListResponse)
async def list_tickets_endpoint(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    ticket_status: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketListResponse:
    """List tickets with optional status, priority, and category filtering."""
    items, total = await list_tickets(
        session,
        status=ticket_status,
        priority=priority,
        category=category,
        limit=limit,
        offset=offset,
    )
    return TicketListResponse(
        items=[TicketResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket_endpoint(
    ticket_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TicketResponse:
    """Retrieve a single ticket by UUID."""
    ticket = await get_ticket_by_id(session, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return TicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket_endpoint(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TicketResponse:
    """Update triage fields or review status for an existing ticket."""
    ticket = await get_ticket_by_id(session, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    updated = await update_ticket(session, ticket, payload)
    return TicketResponse.model_validate(updated)
