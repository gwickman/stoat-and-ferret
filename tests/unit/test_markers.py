# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for timeline markers CRUD, validation, and DI accessibility (BL-419)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.markers_repository import AsyncInMemoryMarkerRepository, Marker
from stoat_ferret.db.models import Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_project(project_id: str = "proj-1") -> Project:
    now = datetime.now(timezone.utc)
    return Project(
        id=project_id,
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )


def _make_app(
    project_repo: AsyncInMemoryProjectRepository | None = None,
    marker_repo: AsyncInMemoryMarkerRepository | None = None,
) -> tuple[object, AsyncInMemoryProjectRepository, AsyncInMemoryMarkerRepository]:
    """Build a test app with injected in-memory repositories."""
    if project_repo is None:
        project_repo = AsyncInMemoryProjectRepository()
    if marker_repo is None:
        marker_repo = AsyncInMemoryMarkerRepository()
    app = create_app(project_repository=project_repo)
    app.state.markers_repository = marker_repo
    return app, project_repo, marker_repo


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


async def test_create_point_marker_returns_201() -> None:
    """POST creates a point marker and returns 201 with full MarkerResponse."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 1.0, "name": "intro", "region_type": "point"},
        )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_id"] == "proj-1"
    assert data["start_time"] == 1.0
    assert data["region_type"] == "point"
    assert data["end_time"] is None
    assert "id" in data
    assert "created_at" in data


async def test_create_section_marker_returns_201() -> None:
    """POST creates a section marker with end_time > start_time."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 0.0, "end_time": 10.0, "name": "intro", "region_type": "section"},
        )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["region_type"] == "section"
    assert data["end_time"] == 10.0


async def test_list_markers_returns_ordered_by_start_time() -> None:
    """GET list returns markers in start_time ASC order."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 5.0, "name": "B"},
        )
        client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 1.0, "name": "A"},
        )
        client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 10.0, "name": "C"},
        )
        resp = client.get("/api/v1/projects/proj-1/markers")

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    assert items[0]["start_time"] == 1.0
    assert items[1]["start_time"] == 5.0
    assert items[2]["start_time"] == 10.0


async def test_patch_marker_updates_mutable_fields() -> None:
    """PATCH updates start_time, end_time, and name."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 1.0, "name": "old"},
        )
        mid = create_resp.json()["id"]
        resp = client.patch(
            f"/api/v1/projects/proj-1/markers/{mid}",
            json={"start_time": 2.0, "name": "new"},
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["start_time"] == 2.0
    assert data["name"] == "new"


async def test_delete_marker_returns_204() -> None:
    """DELETE returns 204 and the marker is gone."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 1.0},
        )
        mid = create_resp.json()["id"]
        resp = client.delete(f"/api/v1/projects/proj-1/markers/{mid}")
        assert resp.status_code == 204

        # Second delete returns 404
        resp2 = client.delete(f"/api/v1/projects/proj-1/markers/{mid}")
        assert resp2.status_code == 404


# ---------------------------------------------------------------------------
# 404 project-not-found tests
# ---------------------------------------------------------------------------


def test_create_marker_unknown_project_returns_404() -> None:
    """POST returns 404 when project_id does not exist."""
    app, _, _ = _make_app()

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/projects/no-such-project/markers",
            json={"start_time": 1.0},
        )
    assert resp.status_code == 404


def test_list_markers_unknown_project_returns_404() -> None:
    """GET list returns 404 when project_id does not exist."""
    app, _, _ = _make_app()

    with TestClient(app) as client:
        resp = client.get("/api/v1/projects/no-such-project/markers")
    assert resp.status_code == 404


async def test_patch_marker_unknown_marker_returns_404() -> None:
    """PATCH returns 404 when marker does not exist."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/v1/projects/proj-1/markers/no-such-marker",
            json={"start_time": 2.0},
        )
    assert resp.status_code == 404


async def test_delete_unknown_marker_returns_404() -> None:
    """DELETE returns 404 when marker does not exist."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        resp = client.delete("/api/v1/projects/proj-1/markers/no-such-marker")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Section overlap validation
# ---------------------------------------------------------------------------


async def test_overlapping_section_markers_rejected_422() -> None:
    """Creating a section marker that overlaps an existing section returns 422."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        # Create first section [0, 10)
        client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 0.0, "end_time": 10.0, "region_type": "section"},
        )
        # Attempt to create overlapping section [5, 15)
        resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 5.0, "end_time": 15.0, "region_type": "section"},
        )
    assert resp.status_code == 422
    assert "must not overlap" in resp.json()["detail"]


async def test_adjacent_section_markers_accepted() -> None:
    """Adjacent (non-overlapping) section markers are allowed."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 0.0, "end_time": 10.0, "region_type": "section"},
        )
        assert r1.status_code == 201, r1.text
        r2 = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 10.0, "end_time": 20.0, "region_type": "section"},
        )
    assert r2.status_code == 201, r2.text


async def test_disjoint_section_markers_accepted() -> None:
    """Non-overlapping disjoint section markers are allowed."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 0.0, "end_time": 5.0, "region_type": "section"},
        )
        resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 10.0, "end_time": 20.0, "region_type": "section"},
        )
    assert resp.status_code == 201, resp.text


async def test_point_markers_have_no_overlap_restriction() -> None:
    """Point markers can overlap freely."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        for _i in range(3):
            resp = client.post(
                "/api/v1/projects/proj-1/markers",
                json={"start_time": 1.0, "region_type": "point"},
            )
            assert resp.status_code == 201, resp.text


# ---------------------------------------------------------------------------
# Parity: point markers accept end_time=None
# ---------------------------------------------------------------------------


async def test_point_marker_accepts_end_time_none() -> None:
    """Point markers accept end_time=None without validation error."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 3.0, "end_time": None, "region_type": "point"},
        )
    assert resp.status_code == 201, resp.text
    assert resp.json()["end_time"] is None


async def test_section_marker_requires_end_time_greater_than_start_time() -> None:
    """Section marker without end_time or with end_time <= start_time is rejected."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        # No end_time
        resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 3.0, "region_type": "section"},
        )
        assert resp.status_code == 422

        # end_time == start_time
        resp2 = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 3.0, "end_time": 3.0, "region_type": "section"},
        )
        assert resp2.status_code == 422


# ---------------------------------------------------------------------------
# region_type immutability
# ---------------------------------------------------------------------------


async def test_patch_cannot_change_region_type() -> None:
    """PATCH does not accept region_type — it is ignored (not in MarkerUpdate schema)."""
    app, project_repo, _ = _make_app()
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 1.0, "region_type": "point"},
        )
        mid = create_resp.json()["id"]
        # Attempt to pass region_type in PATCH body — MarkerUpdate ignores it
        resp = client.patch(
            f"/api/v1/projects/proj-1/markers/{mid}",
            json={"start_time": 2.0, "region_type": "section"},
        )
    assert resp.status_code == 200
    # region_type must remain "point" — MarkerUpdate schema has no region_type field
    assert resp.json()["region_type"] == "point"


# ---------------------------------------------------------------------------
# Cascade delete simulation
# ---------------------------------------------------------------------------


async def test_markers_deleted_with_project_cascade() -> None:
    """Deleting a project removes its markers (FK CASCADE; simulated in-memory)."""
    marker_repo = AsyncInMemoryMarkerRepository()
    project_repo = AsyncInMemoryProjectRepository()
    app, project_repo, marker_repo = _make_app(project_repo, marker_repo)
    await project_repo.add(_make_project())

    with TestClient(app) as client:
        client.post(
            "/api/v1/projects/proj-1/markers",
            json={"start_time": 1.0},
        )
        # Simulate cascade: delete project from repo and clean up markers
        await project_repo.delete("proj-1")
        marker_repo.delete_by_project("proj-1")

        # After project deletion, list returns 404
        resp = client.get("/api/v1/projects/proj-1/markers")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DI accessibility (BL-419-AC-5)
# ---------------------------------------------------------------------------


async def test_markers_repository_accessible_from_app_state() -> None:
    """markers_repository is registered on app.state and get_project_markers is callable."""
    marker_repo = AsyncInMemoryMarkerRepository()
    project_repo = AsyncInMemoryProjectRepository()
    await project_repo.add(_make_project())
    app, _, marker_repo = _make_app(project_repo, marker_repo)

    # Simulate DI access pattern: call get_project_markers directly
    markers = await marker_repo.get_project_markers("proj-1")
    assert markers == []

    # Add a marker and verify retrieval
    marker = Marker(
        id="m-1",
        project_id="proj-1",
        start_time=5.0,
        end_time=None,
        name="test",
        region_type="point",
        created_at=_now_iso(),
    )
    await marker_repo.add(marker)
    markers = await marker_repo.get_project_markers("proj-1")
    assert len(markers) == 1
    assert markers[0].id == "m-1"

    # Verify app.state has the repository registered
    assert hasattr(app.state, "markers_repository")
    retrieved = await app.state.markers_repository.get_project_markers("proj-1")
    assert len(retrieved) == 1
