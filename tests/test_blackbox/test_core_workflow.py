"""Black box tests for core workflows through the REST API.

Tests exercise the complete project → clip lifecycle using only REST API calls.
No internal module imports — all interaction is through HTTP endpoints.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from tests.factories import make_test_video
from tests.test_blackbox.conftest import add_clip_via_api, create_project_via_api

pytestmark = pytest.mark.blackbox


class TestProjectLifecycle:
    """Create, retrieve, list, and delete projects through the API."""

    def test_create_and_retrieve_project(self, client: TestClient) -> None:
        """Create a project and retrieve it by ID."""
        project = create_project_via_api(client, name="My Film")

        resp = client.get(f"/api/v1/projects/{project['id']}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["name"] == "My Film"
        assert data["id"] == project["id"]

    def test_create_project_with_custom_output(self, client: TestClient) -> None:
        """Create a project with custom output settings."""
        project = create_project_via_api(
            client,
            name="4K Project",
            output_width=3840,
            output_height=2160,
            output_fps=60,
        )

        resp = client.get(f"/api/v1/projects/{project['id']}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["output_width"] == 3840
        assert data["output_height"] == 2160
        assert data["output_fps"] == 60

    def test_list_projects(self, client: TestClient) -> None:
        """Create multiple projects and list them."""
        create_project_via_api(client, name="Project A")
        create_project_via_api(client, name="Project B")

        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 2
        names = {p["name"] for p in data["projects"]}
        assert names == {"Project A", "Project B"}

    def test_delete_project(self, client: TestClient) -> None:
        """Create a project, delete it, then verify it's gone."""
        project = create_project_via_api(client, name="Doomed Project")

        resp = client.delete(f"/api/v1/projects/{project['id']}")
        assert resp.status_code == 204

        resp = client.get(f"/api/v1/projects/{project['id']}")
        assert resp.status_code == 404


class TestProjectClipWorkflow:
    """End-to-end project → clip workflow through the API."""

    @pytest.fixture
    async def _seed_video(self, video_repository: AsyncInMemoryVideoRepository) -> dict[str, Any]:
        """Seed a video for clip creation."""
        video = make_test_video()
        await video_repository.add(video)
        return {"id": video.id, "duration_frames": video.duration_frames}

    def test_create_project_add_clip_list_clips(
        self,
        client: TestClient,
        _seed_video: dict[str, Any],
    ) -> None:
        """Full workflow: create project, add clip, list clips."""
        project = create_project_via_api(client, name="Editing Project")
        clip = add_clip_via_api(
            client,
            project_id=project["id"],
            source_video_id=_seed_video["id"],
            in_point=0,
            out_point=100,
            timeline_position=0,
        )

        assert clip["project_id"] == project["id"]
        assert clip["source_video_id"] == _seed_video["id"]

        # List clips for the project
        resp = client.get(f"/api/v1/projects/{project['id']}/clips")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 1
        assert data["clips"][0]["id"] == clip["id"]

    def test_multi_clip_project(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """Create a project with multiple clips from different videos."""
        import asyncio

        # Seed two videos
        video_a = make_test_video(filename="scene_a.mp4")
        video_b = make_test_video(filename="scene_b.mp4")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(video_repository.add(video_a))
        loop.run_until_complete(video_repository.add(video_b))

        project = create_project_via_api(client, name="Multi-Clip Project")

        clip_a = add_clip_via_api(
            client,
            project_id=project["id"],
            source_video_id=video_a.id,
            in_point=0,
            out_point=50,
            timeline_position=0,
        )
        clip_b = add_clip_via_api(
            client,
            project_id=project["id"],
            source_video_id=video_b.id,
            in_point=10,
            out_point=80,
            timeline_position=50,
        )

        resp = client.get(f"/api/v1/projects/{project['id']}/clips")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 2
        clip_ids = {c["id"] for c in data["clips"]}
        assert clip_ids == {clip_a["id"], clip_b["id"]}

    def test_delete_clip_from_project(
        self,
        client: TestClient,
        _seed_video: dict[str, Any],
    ) -> None:
        """Add a clip then delete it, verify it's removed."""
        project = create_project_via_api(client, name="Delete Clip Test")
        clip = add_clip_via_api(
            client,
            project_id=project["id"],
            source_video_id=_seed_video["id"],
        )

        resp = client.delete(f"/api/v1/projects/{project['id']}/clips/{clip['id']}")
        assert resp.status_code == 204

        resp = client.get(f"/api/v1/projects/{project['id']}/clips")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
