"""Operational and AI quality metrics endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.ticket import DashboardMetricsResponse
from app.services.triage import get_dashboard_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_metrics_endpoint(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardMetricsResponse:
    """Return aggregated ticket, LLM analysis, security, and delivery metrics."""
    return await get_dashboard_metrics(session)
