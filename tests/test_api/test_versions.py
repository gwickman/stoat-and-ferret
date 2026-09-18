# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for version API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.models import Project, Track
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository


async def _seed_project_in_db(db: aiosqlite.Connection, project_id: str) -> None:
    """Insert project row into aiosqlite so FK constraints pass in restore tests."""
    now = datetime.now(timezone.utc)
    await db.execute(
        """
        INSERT INTO projects
            (id, name, output_width, output_height, output_fps, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, "Version Test", 1920, 1080, 30, now.isoformat(), now.isoformat()),
    )
    await db.commit()


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
async def test_create_version(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """POST with valid timeline_json returns 201 with VersionResponse."""
    project_id = await _seed_project(project_repository)

    response = client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": '{"clips": [1, 2]}'},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == 1
    assert "created_at" in data
    assert "checksum" in data
    assert len(data["checksum"]) == 64  # SHA-256 hex digest


@pytest.mark.api
def test_create_version_project_not_found(client: TestClient) -> None:
    """POST with non-existent project ID returns 404."""
    response = client.post(
        "/api/v1/projects/nonexistent/versions",
        json={"timeline_json": '{"clips": []}'},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
def test_create_version_empty_body_nonexistent_project(client: TestClient) -> None:
    """POST with empty body (auto-snapshot) returns 404 when project does not exist."""
    response = client.post(
        "/api/v1/projects/some-project/versions",
        json={},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_create_version_incrementing(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Two sequential POSTs produce incrementing version numbers."""
    project_id = await _seed_project(project_repository)

    resp1 = client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": '{"clips": [1]}'},
    )
    assert resp1.status_code == 201
    assert resp1.json()["version_number"] == 1

    resp2 = client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={"timeline_json": '{"clips": [1, 2]}'},
    )
    assert resp2.status_code == 201
    assert resp2.json()["version_number"] == 2


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
    timeline_repository: AsyncInMemoryTimelineRepository,
    db_mock: aiosqlite.Connection,
) -> None:
    """Restore replaces live timeline with the saved snapshot."""
    project_id = await _seed_project(project_repository)
    await _seed_project_in_db(db_mock, project_id)

    # Snapshot version 1 — empty timeline
    resp = client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201

    # Add a track to the live timeline
    track = Track(id="track-snap1", project_id=project_id, track_type="video", label="Track A")
    await timeline_repository.create_track(track)

    # Snapshot version 2 — has track-snap1
    resp = client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201

    # Restore version 1 (empty timeline) — db_mock provides app.state.db for the atomic helper
    response = client.post(f"/api/v1/projects/{project_id}/versions/1/restore")
    assert response.status_code == 200
    data = response.json()
    assert data["restored_version"] == 1
    assert data["new_version"] == 1  # first version written to aiosqlite in this test
    assert "message" in data

    # Behavioral: tracks table must be empty (version 1 had empty timeline)
    cursor = await db_mock.execute("SELECT id FROM tracks WHERE project_id = ?", (project_id,))
    rows = await cursor.fetchall()
    assert rows == [], f"Expected no tracks after restoring empty version 1, got {rows}"

    # Behavioral: restore recorded a new version row in aiosqlite
    cursor = await db_mock.execute(
        "SELECT version_number FROM project_versions WHERE project_id = ?", (project_id,)
    )
    ver_rows = await cursor.fetchall()
    assert len(ver_rows) == 1, f"Expected 1 version in DB after restore, got {ver_rows}"


@pytest.mark.api
async def test_restore_version_modifies_live_timeline(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    db_mock: aiosqlite.Connection,
) -> None:
    """Restore rewrites the live timeline with the snapshot's tracks."""
    project_id = await _seed_project(project_repository)
    await _seed_project_in_db(db_mock, project_id)

    # Add track-a, snapshot version 1
    track_a = Track(id="track-a", project_id=project_id, track_type="video", label="Track A")
    await timeline_repository.create_track(track_a)
    resp = client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201

    # Remove track-a, add track-b, snapshot version 2
    await timeline_repository.delete_track("track-a")
    track_b = Track(id="track-b", project_id=project_id, track_type="audio", label="Track B")
    await timeline_repository.create_track(track_b)
    resp = client.post(f"/api/v1/projects/{project_id}/versions")
    assert resp.status_code == 201

    # Restore version 1 — snapshot contains track-a only
    response = client.post(f"/api/v1/projects/{project_id}/versions/1/restore")
    assert response.status_code == 200
    data = response.json()
    assert data["restored_version"] == 1
    assert data["new_version"] == 1  # first version written to aiosqlite in this test

    # Behavioral: only track-a should be in the DB after restoring version 1
    cursor = await db_mock.execute("SELECT id FROM tracks WHERE project_id = ?", (project_id,))
    rows = await cursor.fetchall()
    track_ids = {r[0] for r in rows}
    assert "track-a" in track_ids, f"Expected track-a after restore, got: {track_ids}"
    assert "track-b" not in track_ids, f"track-b must be absent after restore, got: {track_ids}"


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


@pytest.mark.api
async def test_create_version_with_retention_prunes(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    version_repository: AsyncInMemoryVersionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting retention count prunes old versions after save."""
    project_id = await _seed_project(project_repository)
    monkeypatch.setenv("STOAT_VERSION_RETENTION_COUNT", "3")
    get_settings.cache_clear()

    # Save 5 versions via API
    for i in range(5):
        resp = client.post(
            f"/api/v1/projects/{project_id}/versions",
            json={"timeline_json": f'{{"v": {i + 1}}}'},
        )
        assert resp.status_code == 201

    versions = await version_repository.list_versions(project_id)
    assert len(versions) == 3
    version_numbers = [v.version_number for v in versions]
    assert version_numbers == [5, 4, 3]

    # Cleanup
    get_settings.cache_clear()


@pytest.mark.api
async def test_create_version_no_retention_keeps_all(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    version_repository: AsyncInMemoryVersionRepository,
) -> None:
    """Default (no retention) keeps all versions."""
    get_settings.cache_clear()
    project_id = await _seed_project(project_repository)

    for i in range(5):
        resp = client.post(
            f"/api/v1/projects/{project_id}/versions",
            json={"timeline_json": f'{{"v": {i + 1}}}'},
        )
        assert resp.status_code == 201

    versions = await version_repository.list_versions(project_id)
    assert len(versions) == 5


@pytest.mark.api
async def test_retention_per_project_isolation(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    version_repository: AsyncInMemoryVersionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retention pruning only affects the project being saved."""
    # Create two projects
    now = datetime.now(timezone.utc)
    for pid, name in [("proj-a", "Project A"), ("proj-b", "Project B")]:
        await project_repository.add(
            Project(
                id=pid,
                name=name,
                output_width=1920,
                output_height=1080,
                output_fps=30,
                created_at=now,
                updated_at=now,
            )
        )

    monkeypatch.setenv("STOAT_VERSION_RETENTION_COUNT", "2")
    get_settings.cache_clear()

    # Save 4 versions for project A
    for i in range(4):
        client.post(
            "/api/v1/projects/proj-a/versions",
            json={"timeline_json": f'{{"a": {i + 1}}}'},
        )

    # Save 3 versions for project B
    for i in range(3):
        client.post(
            "/api/v1/projects/proj-b/versions",
            json={"timeline_json": f'{{"b": {i + 1}}}'},
        )

    a_versions = await version_repository.list_versions("proj-a")
    b_versions = await version_repository.list_versions("proj-b")
    assert len(a_versions) == 2
    assert len(b_versions) == 2

    # Cleanup
    get_settings.cache_clear()
