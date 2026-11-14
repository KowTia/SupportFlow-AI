"""Tests for service healthcheck endpoint."""

from httpx import AsyncClient


async def test_healthz_returns_ok_and_connected_db(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "SupportFlow AI"
    assert payload["database"] == "connected"
