"""Smoke tests for project CRUD (UC-03) and project deletion (UC-09).

Validates creating, listing, retrieving, and deleting projects through the
full backend stack.
"""

from __future__ import annotations

import httpx


async def test_uc03_project_crud(smoke_client: httpx.AsyncClient) -> None:
    """Create projects with default and custom settings, list, retrieve, and validate."""
    # Create project with default output settings
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Default Project"},
    )
    assert resp.status_code == 201
    default_proj = resp.json()
    assert default_proj["name"] == "Default Project"
    assert default_proj["output_width"] == 1920
    assert default_proj["output_height"] == 1080
    assert default_proj["output_fps"] == 30

    # Create project with custom output settings
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={
            "name": "Custom Project",
            "output_width": 1280,
            "output_height": 720,
            "output_fps": 60,
        },
    )
    assert resp.status_code == 201
    custom_proj = resp.json()
    assert custom_proj["output_width"] == 1280
    assert custom_proj["output_height"] == 720
    assert custom_proj["output_fps"] == 60

    # List projects — both should appear
    resp = await smoke_client.get("/api/v1/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    project_ids = {p["id"] for p in body["projects"]}
    assert default_proj["id"] in project_ids
    assert custom_proj["id"] in project_ids

    # Retrieve by ID
    resp = await smoke_client.get(f"/api/v1/projects/{custom_proj['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == custom_proj["id"]
    assert resp.json()["name"] == "Custom Project"

    # Validation: empty name returns 422
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": ""},
    )
    assert resp.status_code == 422


async def test_uc09_project_deletion(smoke_client: httpx.AsyncClient) -> None:
    """Delete a project and verify idempotent behavior."""
    # Create a project
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "To Delete"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Delete returns 204
    resp = await smoke_client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 204

    # Re-fetch returns 404
    resp = await smoke_client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404

    # Double-delete returns 404
    resp = await smoke_client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404
