"""Smoke tests for health endpoint startup gate (BL-265).

Verifies end-to-end startup gate behaviour with the real application stack:
- /health/ready returns 503 before startup completes
- /health/ready returns 200 with enriched response after startup
- Startup state (ready flag, timestamp) is correctly set by lifespan
- New subsystem checks (Rust core, filesystem) appear in response
"""

from __future__ import annotations

import httpx
import pytest

from stoat_ferret.api.app import create_app
from tests.conftest import requires_ffmpeg

# ---------------------------------------------------------------------------
# Before-startup gate: 503 without lifespan
# ---------------------------------------------------------------------------


@pytest.fixture
async def unstarted_client() -> httpx.AsyncClient:
    """App created via create_app() but lifespan not run — gate stays closed."""
    app = create_app()
    # _startup_ready == False (default); no lifespan = gate never opens
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_health_ready_503_before_startup_gate(
    unstarted_client: httpx.AsyncClient,
) -> None:
    """GET /health/ready returns 503 with ready=false when gate is closed."""
    resp = await unstarted_client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["ready"] is False


# ---------------------------------------------------------------------------
# After-startup gate: 200 with enriched response (smoke_client runs lifespan)
# ---------------------------------------------------------------------------


@requires_ffmpeg
async def test_health_ready_200_after_startup(smoke_client: httpx.AsyncClient) -> None:
    """GET /health/ready returns 200 with ready=true after full lifespan startup."""
    resp = await smoke_client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True


async def test_health_response_includes_new_fields(smoke_client: httpx.AsyncClient) -> None:
    """GET /health/ready response includes all new fields added in BL-265."""
    resp = await smoke_client.get("/health/ready")
    body = resp.json()

    # New top-level fields
    assert "ready" in body
    assert isinstance(body["ready"], bool)

    assert "app_version" in body
    assert isinstance(body["app_version"], str)
    assert len(body["app_version"]) > 0

    assert "core_version" in body
    # core_version may be None if rust check failed, but should be present
    assert "core_version" in body

    assert "ws_buffer_utilization" in body
    assert isinstance(body["ws_buffer_utilization"], (int, float))
    assert 0.0 <= body["ws_buffer_utilization"] <= 100.0

    assert "uptime_seconds" in body
    # uptime_seconds should be non-negative since startup just completed
    if body["uptime_seconds"] is not None:
        assert body["uptime_seconds"] >= 0.0


async def test_health_new_subsystem_checks_present(smoke_client: httpx.AsyncClient) -> None:
    """GET /health/ready includes rust_core and filesystem in checks dict."""
    resp = await smoke_client.get("/health/ready")
    body = resp.json()
    checks = body["checks"]

    assert "rust_core" in checks
    assert "status" in checks["rust_core"]

    assert "filesystem" in checks
    assert "status" in checks["filesystem"]
    assert checks["filesystem"]["status"] == "ok"


async def test_health_database_check_includes_version(smoke_client: httpx.AsyncClient) -> None:
    """GET /health/ready database check includes sqlite version string."""
    resp = await smoke_client.get("/health/ready")
    body = resp.json()
    db_check = body["checks"]["database"]

    assert db_check["status"] == "ok"
    assert "version" in db_check
    # SQLite version should be a non-empty string (e.g. "3.45.3")
    assert db_check["version"] is not None
    assert isinstance(db_check["version"], str)
    assert len(db_check["version"]) > 0


# ---------------------------------------------------------------------------
# FR-007: deployment.startup state verification
# ---------------------------------------------------------------------------


async def test_startup_ready_flag_set_after_lifespan(
    smoke_client: httpx.AsyncClient,
) -> None:
    """After full lifespan startup, app.state._startup_ready is True.

    The deployment.startup log event is emitted at the same point in the
    lifespan where _startup_ready is set to True. Verifying this flag
    confirms that the event was emitted.
    """
    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    app = transport.app  # type: ignore[union-attr]
    assert app.state._startup_ready is True


async def test_startup_timestamp_set_after_lifespan(
    smoke_client: httpx.AsyncClient,
) -> None:
    """After full lifespan startup, app.state._startup_timestamp is an ISO string."""
    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    app = transport.app  # type: ignore[union-attr]
    assert app.state._startup_timestamp is not None
    # Must be parseable as ISO datetime
    from datetime import datetime

    dt = datetime.fromisoformat(app.state._startup_timestamp)
    assert dt is not None
