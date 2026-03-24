"""Smoke tests for project version listing, creation, and restore.

Validates listing, creating, and restoring project versions through the
full HTTP stack.
"""

from __future__ import annotations

import os

import httpx

from stoat_ferret.api.settings import get_settings


async def test_version_list_empty_project(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/projects/{id}/versions returns 200 with empty list for new project."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # List versions — new project has no versions
    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["versions"] == []
    assert body["limit"] == 20
    assert body["offset"] == 0


async def test_version_create_and_list(smoke_client: httpx.AsyncClient) -> None:
    """POST creates a version snapshot, verify via subsequent GET in the version list."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Create Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Create a version via POST
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": '{"clips": [1, 2, 3]}'},
    )
    assert resp.status_code == 201
    version_data = resp.json()
    assert version_data["version_number"] == 1
    assert "checksum" in version_data
    assert "created_at" in version_data

    # Verify the version appears in GET list
    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["versions"]) == 1
    assert body["versions"][0]["version_number"] == 1
    assert body["versions"][0]["checksum"] == version_data["checksum"]


async def test_version_list_nonexistent_project(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/projects/{id}/versions returns 404 for nonexistent project."""
    resp = await smoke_client.get("/api/v1/projects/nonexistent-id/versions")
    assert resp.status_code == 404


async def test_version_restore(smoke_client: httpx.AsyncClient) -> None:
    """POST restore returns 200 with restored_version and new_version fields."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Restore Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Create a version via POST endpoint
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": '{"timeline": "test"}'},
    )
    assert resp.status_code == 201

    # Restore version 1
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions/1/restore",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["restored_version"] == 1
    assert body["new_version"] == 2
    assert "message" in body


async def test_version_restore_not_found(smoke_client: httpx.AsyncClient) -> None:
    """POST restore for nonexistent version returns 404."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Version Restore 404 Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Restore nonexistent version 999
    resp = await client.post(
        f"/api/v1/projects/{project_id}/versions/999/restore",
    )
    assert resp.status_code == 404


async def test_version_restore_nonexistent_project(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST restore for nonexistent project returns 404."""
    resp = await smoke_client.post(
        "/api/v1/projects/nonexistent-id/versions/1/restore",
    )
    assert resp.status_code == 404


async def test_version_default_retains_all(smoke_client: httpx.AsyncClient) -> None:
    """Default (no retention config) retains all versions."""
    client = smoke_client

    resp = await client.post("/api/v1/projects", json={"name": "Retain All Project"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    for i in range(5):
        resp = await client.post(
            f"/api/v1/projects/{project_id}/versions",
            json={"timeline_json": f'{{"v": {i + 1}}}'},
        )
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


async def test_version_retention_prunes(
    tmp_path: object,
    smoke_client: httpx.AsyncClient,
) -> None:
    """Retention count prunes old versions through the full stack."""
    client = smoke_client

    # Set retention and refresh settings
    orig = os.environ.get("STOAT_VERSION_RETENTION_COUNT")
    os.environ["STOAT_VERSION_RETENTION_COUNT"] = "2"
    get_settings.cache_clear()

    try:
        resp = await client.post("/api/v1/projects", json={"name": "Retention Prune Project"})
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        for i in range(4):
            resp = await client.post(
                f"/api/v1/projects/{project_id}/versions",
                json={"timeline_json": f'{{"v": {i + 1}}}'},
            )
            assert resp.status_code == 201

        resp = await client.get(f"/api/v1/projects/{project_id}/versions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["versions"][0]["version_number"] == 4
        assert body["versions"][1]["version_number"] == 3
    finally:
        if orig is None:
            os.environ.pop("STOAT_VERSION_RETENTION_COUNT", None)
        else:
            os.environ["STOAT_VERSION_RETENTION_COUNT"] = orig
        get_settings.cache_clear()


async def test_version_retention_keep_more_than_total(
    smoke_client: httpx.AsyncClient,
) -> None:
    """keep_count > total versions is a no-op."""
    client = smoke_client

    orig = os.environ.get("STOAT_VERSION_RETENTION_COUNT")
    os.environ["STOAT_VERSION_RETENTION_COUNT"] = "10"
    get_settings.cache_clear()

    try:
        resp = await client.post("/api/v1/projects", json={"name": "Keep More Project"})
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        for i in range(3):
            resp = await client.post(
                f"/api/v1/projects/{project_id}/versions",
                json={"timeline_json": f'{{"v": {i + 1}}}'},
            )
            assert resp.status_code == 201

        resp = await client.get(f"/api/v1/projects/{project_id}/versions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 3
    finally:
        if orig is None:
            os.environ.pop("STOAT_VERSION_RETENTION_COUNT", None)
        else:
            os.environ["STOAT_VERSION_RETENTION_COUNT"] = orig
        get_settings.cache_clear()
