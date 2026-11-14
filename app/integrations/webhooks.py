"""Outbound HMAC-SHA256 webhook dispatcher with dry-run support."""

import hashlib
import hmac
import json
import time
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.analysis import TicketAnalysis
from app.models.ticket import DeliveryLog, DeliveryStatus, DeliveryTarget, Ticket


def compute_hmac_signature(secret: str, raw_body: bytes, timestamp: str) -> str:
    """Compute sha256=<hex> HMAC signature over '<timestamp>.<raw_body>'."""
    signed_message = f"{timestamp}.".encode() + raw_body
    digest = hmac.new(secret.encode("utf-8"), signed_message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_hmac_signature(
    secret: str,
    raw_body: bytes,
    timestamp: str,
    signature_header: str,
) -> bool:
    """Verify an incoming X-SupportFlow-Signature header in constant time."""
    expected = compute_hmac_signature(secret, raw_body, timestamp)
    return hmac.compare_digest(expected, signature_header)


def build_webhook_payload(
    ticket: Ticket,
    latest_analysis: TicketAnalysis | None = None,
) -> dict[str, Any]:
    """Construct canonical JSON-serializable webhook event payload."""
    payload: dict[str, Any] = {
        "event": "ticket.routed",
        "ticket_id": str(ticket.id),
        "source": ticket.source,
        "customer_email": ticket.customer_email,
        "subject": ticket.subject,
        "status": str(ticket.status),
        "category": str(ticket.category) if ticket.category else None,
        "priority": str(ticket.priority) if ticket.priority else None,
        "assigned_team": ticket.assigned_team,
        "draft_reply": ticket.draft_reply,
    }
    if latest_analysis is not None:
        payload["analysis"] = {
            "id": str(latest_analysis.id),
            "provider": latest_analysis.provider,
            "model": latest_analysis.model,
            "confidence": latest_analysis.confidence,
            "cited_kb_ids": latest_analysis.cited_kb_ids,
            "injection_detected": latest_analysis.injection_detected,
            "repair_attempts": latest_analysis.repair_attempts,
        }
    return payload


async def deliver_webhook(
    session: AsyncSession,
    ticket: Ticket,
    *,
    latest_analysis: TicketAnalysis | None = None,
    settings: Settings | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> DeliveryLog:
    """Sign and send an outbound webhook event (or record dry-run audit log)."""
    cfg = settings or get_settings()
    payload = build_webhook_payload(ticket, latest_analysis=latest_analysis)
    raw_body = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")

    timestamp = str(int(time.time()))
    signature = compute_hmac_signature(cfg.webhook_hmac_secret, raw_body, timestamp)
    headers = {
        "Content-Type": "application/json",
        "X-SupportFlow-Event": "ticket.routed",
        "X-SupportFlow-Timestamp": timestamp,
        "X-SupportFlow-Signature": signature,
    }

    if cfg.webhook_dry_run:
        log = DeliveryLog(
            ticket_id=ticket.id,
            target=DeliveryTarget.WEBHOOK,
            endpoint=cfg.webhook_target_url,
            status=DeliveryStatus.DRY_RUN,
            status_code=200,
            attempt=1,
            request_payload={"body": payload, "headers": headers},
            response_body='{"dry_run": true}',
        )
    else:
        status_code: int | None = None
        response_body: str | None = None
        error_message: str | None = None
        delivery_status = DeliveryStatus.FAILED

        try:
            if http_client is not None:
                response = await http_client.post(
                    cfg.webhook_target_url,
                    content=raw_body,
                    headers=headers,
                    timeout=15.0,
                )
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        cfg.webhook_target_url,
                        content=raw_body,
                        headers=headers,
                    )
            status_code = response.status_code
            response_body = response.text[:1000]
            if response.status_code < 400:
                delivery_status = DeliveryStatus.SUCCESS
            else:
                error_message = f"Webhook returned HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            error_message = str(exc)

        log = DeliveryLog(
            ticket_id=ticket.id,
            target=DeliveryTarget.WEBHOOK,
            endpoint=cfg.webhook_target_url,
            status=delivery_status,
            status_code=status_code,
            attempt=1,
            request_payload={"body": payload, "headers": headers},
            response_body=response_body,
            error_message=error_message,
        )

    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
