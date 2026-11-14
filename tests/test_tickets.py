"""Tests for idempotent ticket CRUD endpoints."""

import uuid

from httpx import AsyncClient


async def test_create_ticket_persists_and_returns_201(client: AsyncClient) -> None:
    payload = {
        "subject": "Cannot export monthly invoice PDF",
        "body": "When clicking Download PDF on invoice #4021, the browser returns a 500 error.",
        "source": "web_form",
        "customer_email": "alice@example.com",
        "customer_name": "Alice Mercer",
        "metadata_json": {"plan": "pro"},
    }
    response = await client.post("/api/v1/tickets", json=payload)
    assert response.status_code == 201
    assert response.headers["X-Idempotent-Replay"] == "false"

    data = response.json()
    assert data["subject"] == payload["subject"]
    assert data["status"] == "new"
    assert data["source"] == "web_form"
    assert data["customer_email"] == "alice@example.com"
    assert data["metadata_json"] == {"plan": "pro"}
    assert data["delivery_logs"] == []
    uuid.UUID(data["id"])


async def test_create_ticket_idempotency_via_header_prevents_duplicates(
    client: AsyncClient,
) -> None:
    headers = {"Idempotency-Key": "req-billing-0001"}
    payload = {
        "subject": "Double charge on Visa card",
        "body": "My account was billed twice on November 12 for the Team subscription.",
        "customer_email": "bob@example.com",
    }

    first = await client.post("/api/v1/tickets", json=payload, headers=headers)
    assert first.status_code == 201
    assert first.headers["X-Idempotent-Replay"] == "false"

    second = await client.post(
        "/api/v1/tickets",
        json={**payload, "subject": "Changed subject should still replay original"},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.headers["X-Idempotent-Replay"] == "true"
    assert second.json()["id"] == first.json()["id"]

    listing = await client.get("/api/v1/tickets")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


async def test_create_ticket_without_key_deduplicates_identical_payload(
    client: AsyncClient,
) -> None:
    payload = {
        "subject": "SSO login loops back to login screen",
        "body": "After Okta SAML redirect, the dashboard bounces back to /login.",
        "source": "email",
        "customer_email": "carol@example.com",
    }

    first = await client.post("/api/v1/tickets", json=payload)
    second = await client.post("/api/v1/tickets", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["X-Idempotent-Replay"] == "true"
    assert first.json()["id"] == second.json()["id"]


async def test_list_tickets_pagination_and_filtering(client: AsyncClient) -> None:
    tickets_data = [
        {
            "subject": "Billing question one",
            "body": "Need VAT number added to invoice.",
            "idempotency_key": "k-filter-1",
        },
        {
            "subject": "API latency spike",
            "body": "POST /v1/events timing out above 10s.",
            "idempotency_key": "k-filter-2",
        },
        {
            "subject": "Password reset email missing",
            "body": "Reset link never arrives on corporate domain.",
            "idempotency_key": "k-filter-3",
        },
    ]
    created_ids: list[str] = []
    for item in tickets_data:
        resp = await client.post("/api/v1/tickets", json=item)
        assert resp.status_code == 201
        created_ids.append(resp.json()["id"])

    await client.patch(
        f"/api/v1/tickets/{created_ids[0]}",
        json={"status": "awaiting_review", "priority": "medium", "category": "billing"},
    )
    await client.patch(
        f"/api/v1/tickets/{created_ids[1]}",
        json={"status": "approved", "priority": "critical", "category": "technical"},
    )

    page = await client.get("/api/v1/tickets", params={"limit": 2, "offset": 0})
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 2

    filtered = await client.get(
        "/api/v1/tickets",
        params={"status": "approved", "priority": "critical", "category": "technical"},
    )
    assert filtered.status_code == 200
    filtered_json = filtered.json()
    assert filtered_json["total"] == 1
    assert filtered_json["items"][0]["id"] == created_ids[1]


async def test_get_and_patch_ticket_and_404_handling(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/tickets",
        json={
            "subject": "Webhook signature verification fails",
            "body": "Our consumer fails SHA-256 HMAC validation on retry events.",
            "idempotency_key": "k-patch-1",
        },
    )
    ticket_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/tickets/{ticket_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ticket_id

    patch_resp = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={
            "status": "approved",
            "category": "technical",
            "priority": "high",
            "assigned_team": "integrations",
            "draft_reply": "Please verify the raw request body is hashed before JSON parsing.",
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["status"] == "approved"
    assert updated["category"] == "technical"
    assert updated["priority"] == "high"
    assert updated["assigned_team"] == "integrations"
    assert "raw request body" in updated["draft_reply"]

    missing_id = str(uuid.uuid4())
    assert (await client.get(f"/api/v1/tickets/{missing_id}")).status_code == 404
    assert (
        await client.patch(f"/api/v1/tickets/{missing_id}", json={"status": "approved"})
    ).status_code == 404
