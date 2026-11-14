"""End-to-end ticket triage, approval routing, and dashboard metrics service."""

from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.integrations.google_sheets import export_ticket_to_sheets
from app.integrations.webhooks import deliver_webhook
from app.llm import TicketAnalyzer, build_llm_router
from app.models.analysis import TicketAnalysis
from app.models.ticket import DeliveryLog, DeliveryStatus, Ticket, TicketStatus
from app.rag.embeddings import BaseEmbeddingProvider, build_embedding_provider
from app.schemas.ticket import DashboardMetricsResponse, TicketApproveRequest
from app.services.kb import retrieve_kb_context_for_ticket

_OK_DELIVERY_STATUSES = {DeliveryStatus.SUCCESS, DeliveryStatus.DRY_RUN}


async def dispatch_ticket_integrations(
    session: AsyncSession,
    ticket: Ticket,
    *,
    latest_analysis: TicketAnalysis | None = None,
    settings: Settings | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[DeliveryLog]:
    """Deliver routed ticket payload to webhook and Google Sheets and update ticket status."""
    cfg = settings or get_settings()
    webhook_log = await deliver_webhook(
        session,
        ticket,
        latest_analysis=latest_analysis,
        settings=cfg,
        http_client=http_client,
    )
    sheets_log = await export_ticket_to_sheets(
        session,
        ticket,
        latest_analysis=latest_analysis,
        settings=cfg,
        http_client=http_client,
    )

    logs = [webhook_log, sheets_log]
    all_succeeded = all(log.status in _OK_DELIVERY_STATUSES for log in logs)
    ticket.status = TicketStatus.ROUTED if all_succeeded else TicketStatus.FAILED
    ticket.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(ticket, attribute_names=["analyses", "delivery_logs"])
    return logs


async def analyze_and_triage_ticket(
    session: AsyncSession,
    ticket: Ticket,
    *,
    analyzer: TicketAnalyzer | None = None,
    embedding_provider: BaseEmbeddingProvider | None = None,
    auto_dispatch: bool = True,
    settings: Settings | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[Ticket, TicketAnalysis]:
    """Run RAG lookup, LLM analysis with repair loop, persist analysis, and route or queue."""
    cfg = settings or get_settings()
    resolved_embedding = embedding_provider or build_embedding_provider(cfg)
    resolved_analyzer = analyzer or TicketAnalyzer(
        router=build_llm_router(cfg),
        max_repair_retries=cfg.llm_max_repair_retries,
    )

    ticket.status = TicketStatus.PROCESSING
    await session.commit()

    try:
        kb_context = await retrieve_kb_context_for_ticket(
            session,
            subject=ticket.subject,
            body=ticket.body,
            top_k=cfg.rag_top_k,
            min_score=cfg.rag_min_score,
            embedding_provider=resolved_embedding,
        )
        bundle = await resolved_analyzer.analyze(
            subject=ticket.subject,
            body=ticket.body,
            kb_context=kb_context,
        )
    except Exception:
        ticket.status = TicketStatus.FAILED
        ticket.updated_at = datetime.now(UTC)
        await session.commit()
        raise

    analysis = TicketAnalysis(
        ticket_id=ticket.id,
        provider=bundle.meta.provider,
        model=bundle.meta.model,
        category=bundle.analysis.category,
        priority=bundle.analysis.priority,
        assigned_team=str(bundle.analysis.assigned_team),
        summary=bundle.analysis.summary,
        draft_reply=bundle.analysis.draft_reply,
        confidence=bundle.analysis.confidence,
        needs_human_review=bundle.analysis.needs_human_review,
        reasoning=bundle.analysis.reasoning,
        cited_kb_ids=bundle.analysis.cited_kb_ids,
        injection_detected=bundle.security.detected,
        injection_risk_score=bundle.security.risk_score,
        injection_patterns=bundle.security.matched_patterns,
        repair_attempts=bundle.meta.repair_attempts,
        fallback_used=bundle.meta.fallback_used,
        latency_ms=bundle.meta.latency_ms,
    )
    session.add(analysis)

    ticket.category = bundle.analysis.category
    ticket.priority = bundle.analysis.priority
    ticket.assigned_team = str(bundle.analysis.assigned_team)
    ticket.draft_reply = bundle.analysis.draft_reply
    ticket.status = (
        TicketStatus.AWAITING_REVIEW
        if bundle.analysis.needs_human_review
        else TicketStatus.APPROVED
    )
    ticket.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(analysis)

    if not bundle.analysis.needs_human_review and auto_dispatch:
        await dispatch_ticket_integrations(
            session,
            ticket,
            latest_analysis=analysis,
            settings=cfg,
            http_client=http_client,
        )
    else:
        await session.refresh(ticket, attribute_names=["analyses", "delivery_logs"])

    return ticket, analysis


async def approve_and_route_ticket(
    session: AsyncSession,
    ticket: Ticket,
    payload: TicketApproveRequest,
    *,
    settings: Settings | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> Ticket:
    """Apply operator overrides, approve the ticket, and dispatch outbound integrations."""
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(ticket, field, value)

    ticket.status = TicketStatus.APPROVED
    ticket.updated_at = datetime.now(UTC)
    await session.commit()

    latest_analysis = await session.scalar(
        select(TicketAnalysis)
        .where(TicketAnalysis.ticket_id == ticket.id)
        .order_by(TicketAnalysis.created_at.desc())
    )
    await dispatch_ticket_integrations(
        session,
        ticket,
        latest_analysis=latest_analysis,
        settings=settings,
        http_client=http_client,
    )
    return ticket


async def _grouped_counts(
    session: AsyncSession,
    column: object,
) -> dict[str, int]:
    """Return {string_key: row_count} for a grouped SQLAlchemy column."""
    rows = (await session.execute(select(column, func.count()).group_by(column))).all()  # type: ignore[arg-type]
    result: dict[str, int] = {}
    for key, count in rows:
        label = str(key) if key is not None else "unassigned"
        result[label] = int(count)
    return result


async def get_dashboard_metrics(session: AsyncSession) -> DashboardMetricsResponse:
    """Aggregate ticket, analysis quality, security, and delivery metrics."""
    total_tickets = int(await session.scalar(select(func.count()).select_from(Ticket)) or 0)
    tickets_by_status = await _grouped_counts(session, Ticket.status)
    tickets_by_category = await _grouped_counts(session, Ticket.category)
    tickets_by_priority = await _grouped_counts(session, Ticket.priority)

    analysis_stats = (
        await session.execute(
            select(
                func.count(TicketAnalysis.id),
                func.avg(TicketAnalysis.confidence),
                func.avg(TicketAnalysis.latency_ms),
                func.sum(TicketAnalysis.repair_attempts),
            )
        )
    ).one()

    total_analyses = int(analysis_stats[0] or 0)
    avg_confidence = round(float(analysis_stats[1] or 0.0), 4)
    avg_latency_ms = round(float(analysis_stats[2] or 0.0), 2)
    total_repair_attempts = int(analysis_stats[3] or 0)

    human_review_count = int(
        await session.scalar(
            select(func.count())
            .select_from(TicketAnalysis)
            .where(TicketAnalysis.needs_human_review.is_(True))
        )
        or 0
    )
    injection_detected_count = int(
        await session.scalar(
            select(func.count())
            .select_from(TicketAnalysis)
            .where(TicketAnalysis.injection_detected.is_(True))
        )
        or 0
    )
    human_review_rate = round(human_review_count / total_analyses, 4) if total_analyses > 0 else 0.0

    total_deliveries = int(await session.scalar(select(func.count()).select_from(DeliveryLog)) or 0)
    deliveries_by_status = await _grouped_counts(session, DeliveryLog.status)
    deliveries_by_target = await _grouped_counts(session, DeliveryLog.target)

    return DashboardMetricsResponse(
        total_tickets=total_tickets,
        tickets_by_status=tickets_by_status,
        tickets_by_category=tickets_by_category,
        tickets_by_priority=tickets_by_priority,
        total_analyses=total_analyses,
        avg_confidence=avg_confidence,
        avg_latency_ms=avg_latency_ms,
        human_review_rate=human_review_rate,
        injection_detected_count=injection_detected_count,
        total_repair_attempts=total_repair_attempts,
        total_deliveries=total_deliveries,
        deliveries_by_status=deliveries_by_status,
        deliveries_by_target=deliveries_by_target,
    )
