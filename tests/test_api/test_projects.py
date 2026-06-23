# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for project endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.models import Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository


@pytest.mark.api
def test_list_projects_empty(client: TestClient) -> None:
    """List returns empty when no projects."""
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert data["projects"] == []
    assert data["total"] == 0


@pytest.mark.api
async def test_list_projects_with_data(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """List returns projects when present."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data["projects"]) == 1
    assert data["projects"][0]["id"] == "proj-1"
    assert data["projects"][0]["name"] == "Test Project"
    assert data["total"] == 1


@pytest.mark.api
def test_create_project(client: TestClient) -> None:
    """Create project returns 201."""
    response = client.post(
        "/api/v1/projects",
        json={"name": "My Project"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Project"
    assert data["output_width"] == 1920
    assert data["output_height"] == 1080
    assert data["output_fps"] == 30
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.api
def test_create_project_custom_settings(client: TestClient) -> None:
    """Create project with custom output settings."""
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "4K Project",
            "output_width": 3840,
            "output_height": 2160,
            "output_fps": 60,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["output_width"] == 3840
    assert data["output_height"] == 2160
    assert data["output_fps"] == 60


@pytest.mark.api
def test_create_project_empty_name(client: TestClient) -> None:
    """Create project with empty name returns 422."""
    response = client.post(
        "/api/v1/projects",
        json={"name": ""},
    )
    assert response.status_code == 422


@pytest.mark.api
def test_create_project_invalid_fps(client: TestClient) -> None:
    """Create project with invalid fps returns 422."""
    response = client.post(
        "/api/v1/projects",
        json={"name": "Bad FPS", "output_fps": 200},
    )
    assert response.status_code == 422


@pytest.mark.api
def test_get_project_not_found(client: TestClient) -> None:
    """Get returns 404 for unknown ID."""
    response = client.get("/api/v1/projects/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"
    assert "nonexistent" in data["detail"]["message"]


@pytest.mark.api
async def test_get_project_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Get returns project when found."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    response = client.get("/api/v1/projects/proj-1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "proj-1"
    assert data["name"] == "Test Project"
    assert data["output_width"] == 1920


@pytest.mark.api
def test_delete_project_not_found(client: TestClient) -> None:
    """Delete returns 404 for unknown ID."""
    response = client.delete("/api/v1/projects/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_delete_project_success(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Delete removes project and returns 204."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    response = client.delete("/api/v1/projects/proj-1")
    assert response.status_code == 204

    assert await project_repository.get("proj-1") is None


@pytest.mark.api
async def test_list_projects_respects_limit(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """List respects limit parameter."""
    now = datetime.now(timezone.utc)
    for i in range(5):
        await project_repository.add(
            Project(
                id=f"proj-{i}",
                name=f"Project {i}",
                output_width=1920,
                output_height=1080,
                output_fps=30,
                created_at=now,
                updated_at=now,
            )
        )

    response = client.get("/api/v1/projects?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["projects"]) == 3


@pytest.mark.api
async def test_list_projects_total_is_true_count(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Total reflects true database count, not page size."""
    now = datetime.now(timezone.utc)
    for i in range(25):
        await project_repository.add(
            Project(
                id=f"proj-{i}",
                name=f"Project {i}",
                output_width=1920,
                output_height=1080,
                output_fps=30,
                created_at=now,
                updated_at=now,
            )
        )

    response = client.get("/api/v1/projects?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["projects"]) == 10
    assert data["total"] == 25


@pytest.mark.api
async def test_create_version_no_body_auto_snapshots(
    client: TestClient,
    version_repository: AsyncInMemoryVersionRepository,
) -> None:
    """Body-less POST snapshots the live timeline with a non-empty timeline_json."""
    resp = client.post("/api/v1/projects", json={"name": "Snapshot Project"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201
    data = resp.json()
    assert data["version_number"] == 1
    assert "checksum" in data
    assert "created_at" in data

    # Verify the stored timeline_json contains valid timeline structure
    versions = await version_repository.list_versions(project_id)
    assert len(versions) == 1
    stored = json.loads(versions[0].timeline_json)
    assert "project_id" in stored


@pytest.mark.api
def test_create_version_explicit_timeline_json_backward_compat(
    client: TestClient,
) -> None:
    """POST /versions with explicit timeline_json still returns 201 (backward compat)."""
    resp = client.post("/api/v1/projects", json={"name": "Explicit JSON Project"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": '{"tracks": []}'},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["version_number"] == 1
    assert "checksum" in data
