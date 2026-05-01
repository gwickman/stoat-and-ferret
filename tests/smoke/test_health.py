"""Smoke tests for health check endpoints (UC-08).

Validates the complete fixture chain: app creation -> DI -> ASGITransport
-> HTTP -> response. Tests both liveness and readiness probes.
"""

from __future__ import annotations

from unittest.mock import patch

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
    # Overall may be "degraded" if proxy dir hasn't been created yet or FFmpeg absent
    assert body["status"] in ("ok", "degraded")

    checks = body["checks"]
    assert "database" in checks
    assert checks["database"]["status"] == "ok"
    assert "latency_ms" in checks["database"]
    assert isinstance(checks["database"]["latency_ms"], (int, float))

    assert "ffmpeg" in checks
    assert checks["ffmpeg"]["status"] in ("ok", "unavailable", "degraded", "error")

    assert "preview" in checks
    assert "status" in checks["preview"]
    assert "active_sessions" in checks["preview"]
    assert "cache_usage_percent" in checks["preview"]
    assert isinstance(checks["preview"]["cache_usage_percent"], (int, float))
    assert "cache_healthy" in checks["preview"]
    assert isinstance(checks["preview"]["cache_healthy"], bool)

    assert "proxy" in checks
    assert "status" in checks["proxy"]
    assert "proxy_dir_writable" in checks["proxy"]
    assert isinstance(checks["proxy"]["proxy_dir_writable"], bool)
    assert "pending_proxies" in checks["proxy"]
    assert isinstance(checks["proxy"]["pending_proxies"], int)

    assert "render" in checks
    assert "status" in checks["render"]
    assert checks["render"]["status"] in ("ok", "degraded", "unavailable")
    assert "active_jobs" in checks["render"]
    assert isinstance(checks["render"]["active_jobs"], int)
    assert "queue_depth" in checks["render"]
    assert isinstance(checks["render"]["queue_depth"], int)
    assert "disk_usage_percent" in checks["render"]
    assert isinstance(checks["render"]["disk_usage_percent"], (int, float))
    assert "encoder_available" in checks["render"]
    assert isinstance(checks["render"]["encoder_available"], bool)


async def test_health_ready_without_ffmpeg(smoke_client: httpx.AsyncClient) -> None:
    """FFmpeg absent causes HTTP 200 (not 503); status is ok or degraded."""
    with patch("stoat_ferret.api.routers.health.shutil.which", return_value=None):
        resp = await smoke_client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert body["checks"]["ffmpeg"]["status"] == "unavailable"


async def test_health_ready_degraded_status_structure(smoke_client: httpx.AsyncClient) -> None:
    """Response always contains checks.ffmpeg key regardless of FFmpeg presence."""
    resp = await smoke_client.get("/health/ready")
    body = resp.json()
    assert "ffmpeg" in body["checks"]
    assert "status" in body["checks"]["ffmpeg"]
