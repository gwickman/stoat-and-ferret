"""Smoke tests for GET /api/v1/version endpoint (BL-267)."""

from __future__ import annotations

import httpx


async def test_get_version_returns_200(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/version returns HTTP 200."""
    resp = await smoke_client.get("/api/v1/version")
    assert resp.status_code == 200


async def test_get_version_returns_all_six_fields(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Response exposes the six VersionResponse fields as non-empty strings.

    ``git_sha`` is allowed to be the literal ``"unknown"`` when the build
    system did not capture a SHA, but it must still be a non-empty string.
    ``database_version`` is allowed to be ``"none"`` when alembic has not
    yet recorded a revision, but it must still be a non-empty string.
    """
    resp = await smoke_client.get("/api/v1/version")
    data = resp.json()

    for field in (
        "app_version",
        "core_version",
        "build_timestamp",
        "git_sha",
        "python_version",
        "database_version",
    ):
        assert field in data, f"missing field: {field}"
        assert isinstance(data[field], str), f"{field} must be a string"
        assert len(data[field]) > 0, f"{field} must be non-empty"


async def test_get_version_database_version_is_alembic_revision(
    smoke_client: httpx.AsyncClient,
) -> None:
    """database_version is the alembic revision hash after lifespan migrations.

    After the smoke_client lifespan runs, the database has been migrated to
    head so ``database_version`` should be a non-"none" revision hash.
    """
    resp = await smoke_client.get("/api/v1/version")
    data = resp.json()
    assert data["database_version"] != "none"
