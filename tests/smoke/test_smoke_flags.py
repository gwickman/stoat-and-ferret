"""Smoke tests for GET /api/v1/flags endpoint (BL-268)."""

from __future__ import annotations

import httpx


async def test_get_flags_returns_200(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/flags returns HTTP 200."""
    resp = await smoke_client.get("/api/v1/flags")
    assert resp.status_code == 200


async def test_get_flags_returns_all_four_fields(
    smoke_client: httpx.AsyncClient,
) -> None:
    """GET /api/v1/flags response includes all four STOAT_* boolean flags."""
    resp = await smoke_client.get("/api/v1/flags")
    data = resp.json()

    for field in (
        "testing_mode",
        "seed_endpoint",
        "synthetic_monitoring",
        "batch_rendering",
    ):
        assert field in data, f"missing {field} in /api/v1/flags response"
        assert isinstance(data[field], bool), f"{field} must be a bool"


async def test_get_flags_returns_defaults(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/flags returns the documented defaults under no env overrides."""
    resp = await smoke_client.get("/api/v1/flags")
    data = resp.json()
    assert data["testing_mode"] is False
    assert data["seed_endpoint"] is False
    assert data["synthetic_monitoring"] is False
    assert data["batch_rendering"] is True
