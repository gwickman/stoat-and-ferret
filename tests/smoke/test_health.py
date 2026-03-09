"""Smoke test for health check endpoint (UC-08).

Validates the complete fixture chain: app creation -> DI -> ASGITransport
-> HTTP -> response.
"""

from __future__ import annotations

import httpx


async def test_uc08_health_live(smoke_client: httpx.AsyncClient) -> None:
    """GET /health/live returns status ok, proving the full fixture chain works."""
    resp = await smoke_client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok"}
