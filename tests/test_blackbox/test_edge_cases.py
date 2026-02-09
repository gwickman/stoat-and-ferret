"""Black box tests for edge cases through the REST API.

Tests cover empty results, duplicate handling, concurrent request behavior,
and boundary conditions.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from tests.factories import make_test_video
from tests.test_blackbox.conftest import create_project_via_api

pytestmark = pytest.mark.blackbox


class TestEmptyResults:
    """API behavior when no data exists."""

    def test_list_projects_empty(self, client: TestClient) -> None:
        """List projects returns empty list when none exist."""
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200

        data = resp.json()
        assert data["projects"] == []
        assert data["total"] == 0

    def test_list_videos_empty(self, client: TestClient) -> None:
        """List videos returns empty list when none exist."""
        resp = client.get("/api/v1/videos")
        assert resp.status_code == 200

        data = resp.json()
        assert data["videos"] == []
        assert data["total"] == 0

    def test_search_videos_empty(self, client: TestClient) -> None:
        """Search videos returns empty when no matches."""
        resp = client.get("/api/v1/videos/search", params={"q": "nonexistent"})
        assert resp.status_code == 200

        data = resp.json()
        assert data["videos"] == []
        assert data["total"] == 0
        assert data["query"] == "nonexistent"

    def test_list_clips_empty_project(self, client: TestClient) -> None:
        """List clips returns empty list for project with no clips."""
        project = create_project_via_api(client, name="Empty Project")

        resp = client.get(f"/api/v1/projects/{project['id']}/clips")
        assert resp.status_code == 200

        data = resp.json()
        assert data["clips"] == []
        assert data["total"] == 0

    def test_scan_empty_directory(self, client: TestClient, tmp_path: Any) -> None:
        """Scan an empty directory returns zero counts."""
        resp = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path)},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["scanned"] == 0
        assert data["new"] == 0
        assert data["updated"] == 0
        assert data["errors"] == []


class TestDuplicateHandling:
    """Behavior when creating duplicate or similar resources."""

    def test_duplicate_project_names_allowed(self, client: TestClient) -> None:
        """Two projects with the same name can coexist (different IDs)."""
        proj_a = create_project_via_api(client, name="Same Name")
        proj_b = create_project_via_api(client, name="Same Name")

        assert proj_a["id"] != proj_b["id"]
        assert proj_a["name"] == proj_b["name"]

        # Both appear in listing
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_delete_one_duplicate_preserves_other(self, client: TestClient) -> None:
        """Deleting one project with a duplicate name preserves the other."""
        proj_a = create_project_via_api(client, name="Same Name")
        proj_b = create_project_via_api(client, name="Same Name")

        client.delete(f"/api/v1/projects/{proj_a['id']}")

        # Other project still exists
        resp = client.get(f"/api/v1/projects/{proj_b['id']}")
        assert resp.status_code == 200


class TestConcurrentRequests:
    """Basic concurrent request behavior."""

    def test_concurrent_project_creation(self, client: TestClient) -> None:
        """Multiple concurrent project creations all succeed."""
        project_count = 5

        def create_project(i: int) -> dict[str, Any]:
            resp = client.post("/api/v1/projects", json={"name": f"Concurrent {i}"})
            assert resp.status_code == 201
            return resp.json()

        with ThreadPoolExecutor(max_workers=project_count) as executor:
            results = list(executor.map(create_project, range(project_count)))

        assert len(results) == project_count
        ids = {r["id"] for r in results}
        assert len(ids) == project_count  # All unique IDs

    def test_concurrent_reads_after_write(self, client: TestClient) -> None:
        """Concurrent reads after a write all see the created project."""
        project = create_project_via_api(client, name="Read Target")
        read_count = 5

        def read_project(_: int) -> int:
            resp = client.get(f"/api/v1/projects/{project['id']}")
            return resp.status_code

        with ThreadPoolExecutor(max_workers=read_count) as executor:
            statuses = list(executor.map(read_project, range(read_count)))

        assert all(s == 200 for s in statuses)


class TestPagination:
    """Pagination edge cases."""

    def test_projects_pagination(self, client: TestClient) -> None:
        """Paginated project listing returns correct subsets."""
        for i in range(5):
            create_project_via_api(client, name=f"Project {i}")

        # Get first page
        resp = client.get("/api/v1/projects", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        page1 = resp.json()
        assert len(page1["projects"]) == 2

        # Get second page
        resp = client.get("/api/v1/projects", params={"limit": 2, "offset": 2})
        assert resp.status_code == 200
        page2 = resp.json()
        assert len(page2["projects"]) == 2

        # Pages should have different projects
        page1_ids = {p["id"] for p in page1["projects"]}
        page2_ids = {p["id"] for p in page2["projects"]}
        assert page1_ids.isdisjoint(page2_ids)

    def test_videos_search_with_seeded_data(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """Search returns matching videos from seeded data."""
        import asyncio

        video_a = make_test_video(filename="intro_scene.mp4", path="/v/intro_scene.mp4")
        video_b = make_test_video(filename="outro_scene.mp4", path="/v/outro_scene.mp4")
        video_c = make_test_video(filename="interview.mp4", path="/v/interview.mp4")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(video_repository.add(video_a))
        loop.run_until_complete(video_repository.add(video_b))
        loop.run_until_complete(video_repository.add(video_c))

        # Search for "scene" should match intro and outro
        resp = client.get("/api/v1/videos/search", params={"q": "scene"})
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 2
        filenames = {v["filename"] for v in data["videos"]}
        assert filenames == {"intro_scene.mp4", "outro_scene.mp4"}
