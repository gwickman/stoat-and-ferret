"""Smoke tests for health check endpoints (UC-08).

Validates the complete fixture chain: app creation -> DI -> ASGITransport
-> HTTP -> response. Tests both liveness and readiness probes.
"""

from __future__ import annotations

import httpx


async def test_uc08_health_live(smoke_client: httpx.AsyncClient) -> None:
    """GET /health/live returns status ok, proving the full fixture chain works."""
    resp = await smoke_client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok"}


async def test_uc08_health_ready(smoke_client: httpx.AsyncClient) -> None:
    """GET /health/ready returns status with DB and FFmpeg checks and latency."""
    resp = await smoke_client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"

    checks = body["checks"]
    assert "database" in checks
    assert checks["database"]["status"] == "ok"
    assert "latency_ms" in checks["database"]
    assert isinstance(checks["database"]["latency_ms"], (int, float))

    assert "ffmpeg" in checks
    assert checks["ffmpeg"]["status"] == "ok"
