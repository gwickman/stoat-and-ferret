"""Smoke tests for project version listing, creation, and restore.

Validates listing, creating, and restoring project versions through the
full HTTP stack.
"""

from __future__ import annotations

import httpx


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
