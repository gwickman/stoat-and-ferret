"""Black box tests for error handling through the REST API.

Tests verify that validation errors, not-found errors, and bad requests
return correct HTTP status codes and structured error responses.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from tests.factories import make_test_video
from tests.test_blackbox.conftest import add_clip_via_api, create_project_via_api

pytestmark = pytest.mark.blackbox


class TestNotFoundErrors:
    """404 errors for non-existent resources."""

    def test_get_nonexistent_project(self, client: TestClient) -> None:
        """GET a project that doesn't exist returns 404."""
        resp = client.get("/api/v1/projects/nonexistent-id")
        assert resp.status_code == 404

        detail = resp.json()["detail"]
        assert detail["code"] == "NOT_FOUND"
        assert "nonexistent-id" in detail["message"]

    def test_delete_nonexistent_project(self, client: TestClient) -> None:
        """DELETE a project that doesn't exist returns 404."""
        resp = client.delete("/api/v1/projects/no-such-project")
        assert resp.status_code == 404

        detail = resp.json()["detail"]
        assert detail["code"] == "NOT_FOUND"

    def test_list_clips_nonexistent_project(self, client: TestClient) -> None:
        """List clips for a non-existent project returns 404."""
        resp = client.get("/api/v1/projects/no-such-project/clips")
        assert resp.status_code == 404

        detail = resp.json()["detail"]
        assert detail["code"] == "NOT_FOUND"

    def test_add_clip_nonexistent_project(self, client: TestClient) -> None:
        """Add clip to non-existent project returns 404."""
        resp = client.post(
            "/api/v1/projects/no-such-project/clips",
            json={
                "source_video_id": "some-video",
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 0,
            },
        )
        assert resp.status_code == 404

    def test_add_clip_nonexistent_video(self, client: TestClient) -> None:
        """Add clip referencing non-existent video returns 404."""
        project = create_project_via_api(client, name="Test Project")

        resp = client.post(
            f"/api/v1/projects/{project['id']}/clips",
            json={
                "source_video_id": "nonexistent-video",
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 0,
            },
        )
        assert resp.status_code == 404

        detail = resp.json()["detail"]
        assert detail["code"] == "NOT_FOUND"
        assert "nonexistent-video" in detail["message"]

    def test_get_nonexistent_video(self, client: TestClient) -> None:
        """GET a video that doesn't exist returns 404."""
        resp = client.get("/api/v1/videos/no-such-video")
        assert resp.status_code == 404

        detail = resp.json()["detail"]
        assert detail["code"] == "NOT_FOUND"


class TestValidationErrors:
    """Request validation errors for malformed input."""

    def test_create_project_empty_name(self, client: TestClient) -> None:
        """Create project with empty name returns 422."""
        resp = client.post("/api/v1/projects", json={"name": ""})
        assert resp.status_code == 422

    def test_create_project_missing_name(self, client: TestClient) -> None:
        """Create project without name field returns 422."""
        resp = client.post("/api/v1/projects", json={})
        assert resp.status_code == 422

    def test_create_clip_negative_in_point(
        self,
        client: TestClient,
        seeded_video: dict[str, Any],
    ) -> None:
        """Create clip with negative in_point returns 422."""
        project = create_project_via_api(client)

        resp = client.post(
            f"/api/v1/projects/{project['id']}/clips",
            json={
                "source_video_id": seeded_video["id"],
                "in_point": -1,
                "out_point": 100,
                "timeline_position": 0,
            },
        )
        assert resp.status_code == 422

    def test_scan_invalid_path(self, client: TestClient) -> None:
        """Scan a path that doesn't exist returns 400."""
        resp = client.post(
            "/api/v1/videos/scan",
            json={"path": "/nonexistent/directory/that/does/not/exist"},
        )
        assert resp.status_code == 400

        detail = resp.json()["detail"]
        assert detail["code"] == "INVALID_PATH"


class TestClipValidationErrors:
    """Clip validation errors from the Rust core."""

    @pytest.fixture
    async def _seed_video(self, video_repository: AsyncInMemoryVideoRepository) -> dict[str, Any]:
        """Seed a video with known duration for clip validation tests."""
        video = make_test_video(duration_frames=500)
        await video_repository.add(video)
        return {"id": video.id, "duration_frames": 500}

    def test_clip_out_point_exceeds_duration(
        self,
        client: TestClient,
        _seed_video: dict[str, Any],
    ) -> None:
        """Clip with out_point beyond video duration returns 400."""
        project = create_project_via_api(client)

        resp = client.post(
            f"/api/v1/projects/{project['id']}/clips",
            json={
                "source_video_id": _seed_video["id"],
                "in_point": 0,
                "out_point": 1000,  # exceeds 500 frame duration
                "timeline_position": 0,
            },
        )
        assert resp.status_code == 400

        detail = resp.json()["detail"]
        assert detail["code"] == "VALIDATION_ERROR"

    def test_update_clip_invalid_range(
        self,
        client: TestClient,
        _seed_video: dict[str, Any],
    ) -> None:
        """Update clip to have in_point >= out_point returns 400."""
        project = create_project_via_api(client)
        clip = add_clip_via_api(
            client,
            project_id=project["id"],
            source_video_id=_seed_video["id"],
            in_point=0,
            out_point=100,
            timeline_position=0,
        )

        # Update in_point to be >= out_point
        resp = client.patch(
            f"/api/v1/projects/{project['id']}/clips/{clip['id']}",
            json={"in_point": 200},
        )
        assert resp.status_code == 400

        detail = resp.json()["detail"]
        assert detail["code"] == "VALIDATION_ERROR"
