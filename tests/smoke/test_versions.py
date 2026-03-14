"""Smoke tests for project version listing and restore.

Validates listing and restoring project versions through the full HTTP stack.

Note: The version API exposes list and restore endpoints. Version records
are created internally via version_repo.save() — there is no HTTP endpoint
for creating a version directly. Tests that need a version pre-populated
use the ``create_version_repo`` helper from conftest.
"""

from __future__ import annotations

import httpx

from tests.smoke.conftest import create_version_repo


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

    # Create a version via the repo (no HTTP endpoint for version creation)
    version_repo = create_version_repo(client)
    await version_repo.save(project_id, '{"timeline": "test"}')

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
