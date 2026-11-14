"""Google Sheets ticket exporter with mandatory dry-run mode when keys are absent."""

from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.analysis import TicketAnalysis
from app.models.ticket import DeliveryLog, DeliveryStatus, DeliveryTarget, Ticket


def build_sheets_row(
    ticket: Ticket,
    latest_analysis: TicketAnalysis | None = None,
) -> dict[str, Any]:
    """Format a ticket and latest analysis into a Google Sheets append payload."""
    confidence = f"{latest_analysis.confidence:.2f}" if latest_analysis is not None else ""
    injection_flag = (
        str(latest_analysis.injection_detected).lower() if latest_analysis is not None else "false"
    )
    row = [
        str(ticket.id),
        ticket.created_at.isoformat(),
        ticket.source,
        ticket.customer_email or "",
        ticket.subject,
        str(ticket.category) if ticket.category else "",
        str(ticket.priority) if ticket.priority else "",
        ticket.assigned_team or "",
        str(ticket.status),
        confidence,
        injection_flag,
    ]
    return {
        "range": "Tickets!A:K",
        "majorDimension": "ROWS",
        "valueInputOption": "USER_ENTERED",
        "values": [row],
    }


async def export_ticket_to_sheets(
    session: AsyncSession,
    ticket: Ticket,
    *,
    latest_analysis: TicketAnalysis | None = None,
    settings: Settings | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> DeliveryLog:
    """Append ticket summary row to Google Sheets or log dry-run export payload."""
    cfg = settings or get_settings()
    endpoint = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{cfg.google_sheets_spreadsheet_id}"
        "/values/Tickets!A:K:append"
    )
    row_payload = build_sheets_row(ticket, latest_analysis=latest_analysis)

    if cfg.google_sheets_dry_run or not cfg.google_sheets_credentials_json.strip():
        log = DeliveryLog(
            ticket_id=ticket.id,
            target=DeliveryTarget.GOOGLE_SHEETS,
            endpoint=endpoint,
            status=DeliveryStatus.DRY_RUN,
            status_code=200,
            attempt=1,
            request_payload=row_payload,
            response_body='{"dry_run": true, "updatedRows": 1}',
        )
    else:
        status_code: int | None = None
        response_body: str | None = None
        error_message: str | None = None
        delivery_status = DeliveryStatus.FAILED
        headers = {
            "Authorization": f"Bearer {cfg.google_sheets_credentials_json.strip()}",
            "Content-Type": "application/json",
        }

        try:
            if http_client is not None:
                response = await http_client.post(
                    endpoint,
                    params={"valueInputOption": row_payload["valueInputOption"]},
                    json={"majorDimension": "ROWS", "values": row_payload["values"]},
                    headers=headers,
                    timeout=15.0,
                )
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        endpoint,
                        params={"valueInputOption": row_payload["valueInputOption"]},
                        json={"majorDimension": "ROWS", "values": row_payload["values"]},
                        headers=headers,
                    )
            status_code = response.status_code
            response_body = response.text[:1000]
            if response.status_code < 400:
                delivery_status = DeliveryStatus.SUCCESS
            else:
                error_message = f"Google Sheets returned HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            error_message = str(exc)

        log = DeliveryLog(
            ticket_id=ticket.id,
            target=DeliveryTarget.GOOGLE_SHEETS,
            endpoint=endpoint,
            status=delivery_status,
            status_code=status_code,
            attempt=1,
            request_payload=row_payload,
            response_body=response_body,
            error_message=error_message,
        )

    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
