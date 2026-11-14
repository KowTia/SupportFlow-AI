"""Celery task definitions for background ticket triage and delivery."""

import asyncio
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_session_factory
from app.models.analysis import TicketAnalysis
from app.services.tickets import get_ticket_by_id
from app.services.triage import analyze_and_triage_ticket, dispatch_ticket_integrations
from app.workers.celery_app import celery_app


async def run_triage_for_ticket_id(
    ticket_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> dict[str, Any]:
    """Execute async triage pipeline for a ticket ID inside an isolated DB session."""
    factory = session_factory or get_session_factory()
    async with factory() as session:
        ticket = await get_ticket_by_id(session, ticket_id)
        if ticket is None:
            return {"ticket_id": str(ticket_id), "status": "not_found"}

        updated_ticket, analysis = await analyze_and_triage_ticket(session, ticket)
        return {
            "ticket_id": str(updated_ticket.id),
            "status": str(updated_ticket.status),
            "analysis_id": str(analysis.id),
            "needs_human_review": analysis.needs_human_review,
        }


async def run_dispatch_for_ticket_id(
    ticket_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> dict[str, Any]:
    """Execute async outbound webhook and Google Sheets dispatch for a ticket ID."""
    factory = session_factory or get_session_factory()
    async with factory() as session:
        ticket = await get_ticket_by_id(session, ticket_id)
        if ticket is None:
            return {"ticket_id": str(ticket_id), "status": "not_found"}

        latest_analysis = await session.scalar(
            select(TicketAnalysis)
            .where(TicketAnalysis.ticket_id == ticket.id)
            .order_by(TicketAnalysis.created_at.desc())
        )
        logs = await dispatch_ticket_integrations(
            session,
            ticket,
            latest_analysis=latest_analysis,
        )
        return {
            "ticket_id": str(ticket.id),
            "status": str(ticket.status),
            "deliveries": [{"target": str(log.target), "status": str(log.status)} for log in logs],
        }


@celery_app.task(name="supportflow.triage_ticket")
def triage_ticket_task(ticket_id: str) -> dict[str, Any]:
    """Celery task wrapper to run ticket triage asynchronously."""
    return asyncio.run(run_triage_for_ticket_id(uuid.UUID(ticket_id)))


@celery_app.task(name="supportflow.dispatch_ticket")
def dispatch_ticket_task(ticket_id: str) -> dict[str, Any]:
    """Celery task wrapper to dispatch outbound webhook and Google Sheets updates."""
    return asyncio.run(run_dispatch_for_ticket_id(uuid.UUID(ticket_id)))
