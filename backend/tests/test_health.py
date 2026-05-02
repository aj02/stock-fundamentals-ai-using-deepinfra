"""/health is the cheap liveness probe — no DB, no Redis, always 200."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_ok_with_disclaimer(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert "disclaimer" in body
    assert "investment advice" in body["disclaimer"].lower()
