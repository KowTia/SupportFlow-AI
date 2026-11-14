"""Service layer for idempotent ticket creation, querying, and updates."""

import hashlib
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.schemas.ticket import TicketCreate, TicketUpdate


def resolve_idempotency_key(payload: TicketCreate, header_key: str | None = None) -> str:
    """Resolve an idempotency key from header, body, or deterministic content hash."""
    if header_key is not None and header_key.strip():
        return header_key.strip()
    if payload.idempotency_key is not None and payload.idempotency_key.strip():
        return payload.idempotency_key.strip()

    normalized_email = (payload.customer_email or "").strip().lower()
    raw_fingerprint = (
        f"{payload.source.strip()}:{normalized_email}:"
        f"{payload.subject.strip()}:{payload.body.strip()}"
    )
    return hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()


async def create_ticket_idempotent(
    session: AsyncSession,
    payload: TicketCreate,
    header_key: str | None = None,
) -> tuple[Ticket, bool]:
    """Create a ticket or return the existing record matching the resolved idempotency key."""
    key = resolve_idempotency_key(payload, header_key)

    existing = await session.scalar(select(Ticket).where(Ticket.idempotency_key == key))
    if existing is not None:
        return existing, False

    ticket = Ticket(
        idempotency_key=key,
        source=payload.source.strip(),
        customer_email=str(payload.customer_email) if payload.customer_email else None,
        customer_name=payload.customer_name.strip() if payload.customer_name else None,
        subject=payload.subject.strip(),
        body=payload.body.strip(),
        metadata_json=payload.metadata_json,
    )
    session.add(ticket)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(Ticket).where(Ticket.idempotency_key == key))
        if existing is not None:
            return existing, False
        raise

    await session.refresh(ticket)
    return ticket, True


async def list_tickets(
    session: AsyncSession,
    *,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Ticket], int]:
    """Return filtered, paginated tickets alongside the total matching row count."""
    conditions = []
    if status is not None:
        conditions.append(Ticket.status == status)
    if priority is not None:
        conditions.append(Ticket.priority == priority)
    if category is not None:
        conditions.append(Ticket.category == category)

    count_stmt = select(func.count()).select_from(Ticket)
    data_stmt = select(Ticket).order_by(Ticket.created_at.desc())

    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        data_stmt = data_stmt.where(condition)

    total = await session.scalar(count_stmt) or 0
    rows = await session.scalars(data_stmt.offset(offset).limit(limit))
    return list(rows.all()), int(total)


async def get_ticket_by_id(session: AsyncSession, ticket_id: uuid.UUID) -> Ticket | None:
    """Fetch a single ticket by primary key UUID."""
    return await session.scalar(select(Ticket).where(Ticket.id == ticket_id))


async def update_ticket(
    session: AsyncSession,
    ticket: Ticket,
    payload: TicketUpdate,
) -> Ticket:
    """Apply partial updates to an existing ticket and persist them."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(ticket, field, value)

    await session.commit()
    await session.refresh(ticket)
    return ticket
