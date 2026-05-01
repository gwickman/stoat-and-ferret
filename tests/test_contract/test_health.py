"""Contract tests for health endpoint startup gate and subsystem checks (BL-265).

Verifies observable HTTP behaviour of the /health/ready endpoint:
- Returns 503 with ready=false before startup completes (startup gate)
- Returns 200 with ready=true when all critical checks pass
- Response includes version info and operational metrics fields
- Each subsystem check (database, Rust core, filesystem) works independently
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import get_settings
from tests.conftest import requires_ffmpeg


@pytest.fixture
async def not_ready_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """App with startup gate closed (default False from create_app)."""
    app = create_app()
    # _startup_ready defaults to False via create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture
async def ready_client(tmp_path: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    """App with startup gate open, db path in tmp_path, no real services injected."""
    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    os.environ["STOAT_DATABASE_PATH"] = str(tmp_path / "contract_test.db")
    get_settings.cache_clear()

    app = create_app()
    # Open the startup gate manually (as lifespan would do in production)
    app.state._startup_ready = True
    app.state._startup_timestamp = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# FR-001: 503 before startup complete
# ---------------------------------------------------------------------------


async def test_health_ready_503_on_startup(
    not_ready_client: httpx.AsyncClient,
) -> None:
    """GET /health/ready returns 503 with ready=false when startup gate is closed."""
    resp = await not_ready_client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["ready"] is False
    assert body["status"] == "starting"


async def test_health_ready_503_response_structure(
    not_ready_client: httpx.AsyncClient,
) -> None:
    """503 response includes required fields: ready, status, app_version."""
    resp = await not_ready_client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert "ready" in body
    assert "status" in body
    assert "app_version" in body
    assert isinstance(body["app_version"], str)


# ---------------------------------------------------------------------------
# FR-002: 200 when all checks pass
# ---------------------------------------------------------------------------


@requires_ffmpeg
async def test_health_ready_200_when_ready(ready_client: httpx.AsyncClient) -> None:
    """GET /health/ready returns 200 with ready=true when startup gate is open."""
    resp = await ready_client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True


# ---------------------------------------------------------------------------
# FR-006: Response includes version info
# ---------------------------------------------------------------------------


async def test_health_response_includes_app_version(
    ready_client: httpx.AsyncClient,
) -> None:
    """GET /health/ready includes non-empty app_version in response."""
    resp = await ready_client.get("/health/ready")
    body = resp.json()
    assert "app_version" in body
    assert isinstance(body["app_version"], str)
    assert len(body["app_version"]) > 0


async def test_health_response_includes_uptime(
    ready_client: httpx.AsyncClient,
) -> None:
    """GET /health/ready includes non-negative uptime_seconds when startup timestamp set."""
    resp = await ready_client.get("/health/ready")
    body = resp.json()
    assert "uptime_seconds" in body
    assert body["uptime_seconds"] is not None
    assert body["uptime_seconds"] >= 0.0


async def test_health_response_includes_ws_buffer_utilization(
    ready_client: httpx.AsyncClient,
) -> None:
    """GET /health/ready includes ws_buffer_utilization in range [0, 100]."""
    resp = await ready_client.get("/health/ready")
    body = resp.json()
    assert "ws_buffer_utilization" in body
    assert 0.0 <= body["ws_buffer_utilization"] <= 100.0


# ---------------------------------------------------------------------------
# FR-003: Database check
# ---------------------------------------------------------------------------


async def test_database_check_ok_when_no_db(ready_client: httpx.AsyncClient) -> None:
    """Database check returns ok when no db is injected (DI mode without real db)."""
    resp = await ready_client.get("/health/ready")
    body = resp.json()
    assert "database" in body["checks"]
    assert body["checks"]["database"]["status"] == "ok"


# ---------------------------------------------------------------------------
# FR-004: Rust core check (unit-level)
# ---------------------------------------------------------------------------


async def test_rust_core_check_returns_ok() -> None:
    """_check_rust_core returns ok status with non-empty version string."""
    from stoat_ferret.api.routers.health import _check_rust_core

    result = await _check_rust_core()
    assert result["status"] == "ok"
    assert "version" in result
    assert isinstance(result["version"], str)
    assert len(result["version"]) > 0


async def test_rust_core_check_in_response(ready_client: httpx.AsyncClient) -> None:
    """GET /health/ready includes rust_core check with ok status."""
    resp = await ready_client.get("/health/ready")
    body = resp.json()
    assert "rust_core" in body["checks"]
    assert body["checks"]["rust_core"]["status"] == "ok"
    assert "version" in body["checks"]["rust_core"]


# ---------------------------------------------------------------------------
# FR-005: Filesystem check (unit-level)
# ---------------------------------------------------------------------------


async def test_filesystem_check_returns_ok(tmp_path: Path) -> None:
    """_check_filesystem returns ok when data directory is writable."""
    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    os.environ["STOAT_DATABASE_PATH"] = str(tmp_path / "fs_test.db")
    get_settings.cache_clear()

    from stoat_ferret.api.routers.health import _check_filesystem

    result = await _check_filesystem()
    assert result["status"] == "ok"

    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db
    get_settings.cache_clear()


async def test_filesystem_check_in_response(ready_client: httpx.AsyncClient) -> None:
    """GET /health/ready includes filesystem check with ok status."""
    resp = await ready_client.get("/health/ready")
    body = resp.json()
    assert "filesystem" in body["checks"]
    assert body["checks"]["filesystem"]["status"] == "ok"
