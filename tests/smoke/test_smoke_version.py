"""Smoke tests for GET /api/v1/version endpoint (BL-263)."""

from __future__ import annotations

import httpx


async def test_get_version_returns_200(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/version returns HTTP 200."""
    resp = await smoke_client.get("/api/v1/version")
    assert resp.status_code == 200


async def test_get_version_includes_app_version(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/version response includes a non-empty app_version string."""
    resp = await smoke_client.get("/api/v1/version")
    data = resp.json()
    assert "app_version" in data
    assert isinstance(data["app_version"], str)
    assert len(data["app_version"]) > 0


async def test_get_version_includes_core_status(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/version response includes a non-empty core_status string."""
    resp = await smoke_client.get("/api/v1/version")
    data = resp.json()
    assert "core_status" in data
    assert isinstance(data["core_status"], str)
    assert len(data["core_status"]) > 0
