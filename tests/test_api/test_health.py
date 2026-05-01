"""Tests for health check endpoints."""

from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.routers.health import _check_ffmpeg
from tests.conftest import requires_ffmpeg


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
def test_readiness_without_ffmpeg_returns_200(client: TestClient) -> None:
    """Readiness returns 200 (not 503) when FFmpeg is absent — FFmpeg is non-critical."""
    with patch("stoat_ferret.api.routers.health.shutil.which", return_value=None):
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["ffmpeg"]["status"] == "unavailable"


@pytest.mark.api
def test_readiness_without_ffmpeg_status_degraded(client: TestClient) -> None:
    """Readiness returns degraded status when FFmpeg is unavailable."""
    with patch(
        "stoat_ferret.api.routers.health._check_ffmpeg",
        new_callable=AsyncMock,
        return_value={"status": "unavailable"},
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"


@pytest.mark.api
def test_readiness_without_ffmpeg_ffmpeg_check_in_response(client: TestClient) -> None:
    """Readiness includes ffmpeg check with unavailable status in response."""
    with patch(
        "stoat_ferret.api.routers.health._check_ffmpeg",
        new_callable=AsyncMock,
        return_value={"status": "unavailable"},
    ):
        response = client.get("/health/ready")

    data = response.json()
    assert "ffmpeg" in data["checks"]
    assert data["checks"]["ffmpeg"]["status"] == "unavailable"


@pytest.mark.api
def test_readiness_ffmpeg_error_returns_200(client: TestClient) -> None:
    """Readiness returns 200 when ffmpeg command fails — FFmpeg is non-critical."""
    with (
        patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
    ):
        mock_run.side_effect = Exception("Command timed out")
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["ffmpeg"]["status"] == "error"
    assert "Command timed out" in data["checks"]["ffmpeg"]["error"]


@pytest.mark.api
def test_readiness_ffmpeg_timeout_returns_200(client: TestClient) -> None:
    """Readiness returns 200 when FFmpeg check times out — FFmpeg is non-critical."""
    with patch(
        "stoat_ferret.api.routers.health._check_ffmpeg",
        new_callable=AsyncMock,
        side_effect=asyncio.TimeoutError,
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["ffmpeg"]["status"] == "error"
    assert data["checks"]["ffmpeg"]["error"] == "check timed out"


@requires_ffmpeg
@pytest.mark.api
def test_readiness_with_ffmpeg_returns_200_ok(client: TestClient) -> None:
    """Readiness returns 200 with status ok when FFmpeg is available."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["status"] == "ok"
    assert data["checks"]["ffmpeg"]["status"] == "ok"


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
    elif ffmpeg_check["status"] == "error":
        assert "error" in ffmpeg_check
    # "unavailable" status has no additional required fields

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


# ---------------------------------------------------------------------------
# Interface contract tests for _check_ffmpeg()
# ---------------------------------------------------------------------------


async def test_check_ffmpeg_parses_first_line() -> None:
    """_check_ffmpeg extracts version from the first line of ffmpeg output."""
    with (
        patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(
            stdout="ffmpeg version 6.0 Copyright (c) 2000-2023 the FFmpeg developers\n"
        )
        result = await _check_ffmpeg()

    assert result["status"] == "ok"
    assert result["version"] == "6.0"


async def test_check_ffmpeg_handles_git_build_version() -> None:
    """_check_ffmpeg accepts git-build version strings (e.g., N-113007-g4f08a56)."""
    with (
        patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(
            stdout="ffmpeg version N-113007-g4f08a56 Copyright (c) 2000-2023\n"
        )
        result = await _check_ffmpeg()

    assert result["status"] == "ok"
    assert result["version"] == "N-113007-g4f08a56"


async def test_check_ffmpeg_absent_returns_unavailable() -> None:
    """_check_ffmpeg returns unavailable status when binary is not in PATH."""
    with patch("stoat_ferret.api.routers.health.shutil.which", return_value=None):
        result = await _check_ffmpeg()

    assert result == {"status": "unavailable"}
    assert "error" not in result


async def test_check_ffmpeg_timeout_returns_error() -> None:
    """_check_ffmpeg returns error status when subprocess times out; no exception raised."""
    with (
        patch("stoat_ferret.api.routers.health.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("stoat_ferret.api.routers.health.subprocess.run") as mock_run,
    ):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=5)
        result = await _check_ffmpeg()

    assert result["status"] == "error"
    assert "error" in result
