"""Tests for version API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.models import Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository


async def _seed_project(repo: AsyncInMemoryProjectRepository) -> str:
    """Create a test project and return its ID."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-v1",
        name="Version Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await repo.add(project)
    return project.id


@pytest.mark.api
async def test_list_versions_empty(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """List returns empty when project has no versions."""
    project_id = await _seed_project(project_repository)

    response = client.get(f"/api/v1/projects/{project_id}/versions")
    assert response.status_code == 200
    data = response.json()
    assert data["versions"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.api
async def test_list_versions_with_data(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    version_repository: AsyncInMemoryVersionRepository,
) -> None:
    """List returns versions when present."""
    project_id = await _seed_project(project_repository)
    await version_repository.save(project_id, '{"clips": []}')
    await version_repository.save(project_id, '{"clips": [1]}')

    response = client.get(f"/api/v1/projects/{project_id}/versions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["versions"]) == 2
    # Most recent first (descending order)
    assert data["versions"][0]["version_number"] == 2
    assert data["versions"][1]["version_number"] == 1
    assert "created_at" in data["versions"][0]
    assert "checksum" in data["versions"][0]


@pytest.mark.api
async def test_list_versions_pagination(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    version_repository: AsyncInMemoryVersionRepository,
) -> None:
    """List respects limit and offset pagination."""
    project_id = await _seed_project(project_repository)
    for i in range(5):
        await version_repository.save(project_id, f'{{"v": {i}}}')

    response = client.get(f"/api/v1/projects/{project_id}/versions?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["versions"]) == 2


@pytest.mark.api
def test_list_versions_project_not_found(client: TestClient) -> None:
    """List returns 404 for non-existent project."""
    response = client.get("/api/v1/projects/nonexistent/versions")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_restore_version(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    version_repository: AsyncInMemoryVersionRepository,
) -> None:
    """Restore creates a new version from old state."""
    project_id = await _seed_project(project_repository)
    await version_repository.save(project_id, '{"clips": [1]}')
    await version_repository.save(project_id, '{"clips": [1, 2]}')

    response = client.post(f"/api/v1/projects/{project_id}/versions/1/restore")
    assert response.status_code == 200
    data = response.json()
    assert data["restored_version"] == 1
    assert data["new_version"] == 3
    assert "message" in data


@pytest.mark.api
async def test_restore_version_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Restore returns 404 for non-existent version."""
    project_id = await _seed_project(project_repository)

    response = client.post(f"/api/v1/projects/{project_id}/versions/999/restore")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "PROJECT_VERSION_NOT_FOUND"


@pytest.mark.api
def test_restore_version_project_not_found(client: TestClient) -> None:
    """Restore returns 404 for non-existent project."""
    response = client.post("/api/v1/projects/nonexistent/versions/1/restore")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"
