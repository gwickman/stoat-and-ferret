"""Smoke tests for project version listing.

Validates listing project versions through the full HTTP stack.

Note: The version API exposes list and restore endpoints. Version records
are created internally via version_repo.save() — there is no HTTP endpoint
for creating a version directly. This test validates the list endpoint
returns 200 for a valid project.
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


async def test_version_list_nonexistent_project(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/projects/{id}/versions returns 404 for nonexistent project."""
    resp = await smoke_client.get("/api/v1/projects/nonexistent-id/versions")
    assert resp.status_code == 404
