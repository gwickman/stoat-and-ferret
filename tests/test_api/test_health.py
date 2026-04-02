"""Tests for health check endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_liveness_returns_ok(client: TestClient) -> None:
    """Liveness endpoint always returns 200 with status ok."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.api
def test_readiness_returns_200_when_healthy(client: TestClient) -> None:
    """Readiness returns 200 when all dependency checks pass."""
    # Patch ffmpeg check to always succeed (no DB in injection mode, health check skips it)
    with (
        patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0 Copyright (c) 2000-2023\n")
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "checks" in data
    assert data["checks"]["database"]["status"] == "ok"
    assert "latency_ms" in data["checks"]["database"]
    assert data["checks"]["ffmpeg"]["status"] == "ok"
    assert data["checks"]["ffmpeg"]["version"] == "6.0"


@pytest.mark.api
def test_readiness_returns_503_when_database_unavailable(client: TestClient) -> None:
    """Readiness returns 503 when database check fails."""
    # Set a mock db on app.state to simulate a broken database connection
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("Database connection lost")
    client.app.state.db = mock_db  # type: ignore[union-attr]

    # Also patch ffmpeg to succeed so we isolate database failure
    with (
        patch(
            "stoat_ferret.api.routers.health.shutil.which",
            return_value="/usr/bin/ffmpeg",
        ),
        patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0 Copyright (c) 2000-2023\n")
        response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"]["status"] == "error"
    assert "Database connection lost" in data["checks"]["database"]["error"]

    # Clean up: remove mock db so it doesn't affect other tests
    del client.app.state.db  # type: ignore[union-attr]


@pytest.mark.api
def test_readiness_returns_503_when_ffmpeg_unavailable(client: TestClient) -> None:
    """Readiness returns 503 when ffmpeg is not found."""
    # Patch ffmpeg to not be found
    with patch("stoat_ferret.api.routers.health.shutil.which", return_value=None):
        response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["ffmpeg"]["status"] == "error"
    assert "not found" in data["checks"]["ffmpeg"]["error"]


@pytest.mark.api
def test_readiness_returns_503_when_ffmpeg_fails(client: TestClient) -> None:
    """Readiness returns 503 when ffmpeg command fails."""
    with (
        patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
    ):
        mock_run.side_effect = Exception("Command timed out")
        response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["ffmpeg"]["status"] == "error"
    assert "Command timed out" in data["checks"]["ffmpeg"]["error"]


@pytest.mark.api
def test_readiness_structure(client: TestClient) -> None:
    """Readiness response has correct structure regardless of health status."""
    response = client.get("/health/ready")
    data = response.json()

    # Check structure
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]
    assert "ffmpeg" in data["checks"]
    assert "preview" in data["checks"]
    assert "proxy" in data["checks"]
    assert "render" in data["checks"]

    # Database check has expected fields
    db_check = data["checks"]["database"]
    assert "status" in db_check
    if db_check["status"] == "ok":
        assert "latency_ms" in db_check
    else:
        assert "error" in db_check

    # FFmpeg check has expected fields
    ffmpeg_check = data["checks"]["ffmpeg"]
    assert "status" in ffmpeg_check
    if ffmpeg_check["status"] == "ok":
        assert "version" in ffmpeg_check
    else:
        assert "error" in ffmpeg_check

    # Preview check has expected fields
    preview_check = data["checks"]["preview"]
    assert "status" in preview_check
    if preview_check["status"] != "degraded" or "error" not in preview_check:
        assert "active_sessions" in preview_check
        assert "cache_usage_percent" in preview_check
        assert "cache_healthy" in preview_check

    # Proxy check has expected fields
    proxy_check = data["checks"]["proxy"]
    assert "status" in proxy_check
    if proxy_check["status"] != "degraded" or "error" not in proxy_check:
        assert "proxy_dir_writable" in proxy_check
        assert "pending_proxies" in proxy_check

    # Render check has expected fields
    render_check = data["checks"]["render"]
    assert "status" in render_check
    if render_check["status"] != "degraded" or "error" not in render_check:
        assert "active_jobs" in render_check
        assert "queue_depth" in render_check
        assert "disk_usage_percent" in render_check
        assert "encoder_available" in render_check
