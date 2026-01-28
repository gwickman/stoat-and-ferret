"""Tests for clip endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from tests.test_repository_contract import make_test_video


@pytest.mark.api
async def test_list_clips_empty(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """List returns empty when no clips."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    response = client.get("/api/v1/projects/proj-1/clips")
    assert response.status_code == 200
    data = response.json()
    assert data["clips"] == []
    assert data["total"] == 0


@pytest.mark.api
def test_list_clips_project_not_found(client: TestClient) -> None:
    """List clips returns 404 for unknown project."""
    response = client.get("/api/v1/projects/nonexistent/clips")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_add_clip(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Add clip returns 201."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    video = make_test_video()
    await video_repository.add(video)

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "source_video_id": video.id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert data["source_video_id"] == video.id
    assert data["in_point"] == 0
    assert data["out_point"] == 100
    assert data["timeline_position"] == 0
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.api
def test_add_clip_project_not_found(client: TestClient) -> None:
    """Add clip returns 404 for unknown project."""
    response = client.post(
        "/api/v1/projects/nonexistent/clips",
        json={
            "source_video_id": "video-1",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 404


@pytest.mark.api
async def test_add_clip_video_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Add clip returns 404 for unknown video."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "source_video_id": "nonexistent",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"
    assert "nonexistent" in data["detail"]["message"]


@pytest.mark.api
async def test_add_clip_invalid_validation(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Add clip returns 400 for invalid clip (out_point <= in_point)."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    video = make_test_video()
    await video_repository.add(video)

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "source_video_id": video.id,
            "in_point": 100,
            "out_point": 50,  # Invalid: out < in
            "timeline_position": 0,
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "VALIDATION_ERROR"


@pytest.mark.api
def test_delete_clip_not_found(client: TestClient) -> None:
    """Delete clip returns 404 for unknown clip."""
    response = client.delete("/api/v1/projects/proj-1/clips/nonexistent")
    assert response.status_code == 404


@pytest.mark.api
async def test_delete_clip_success(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Delete clip removes it and returns 204."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    video = make_test_video()
    await video_repository.add(video)

    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    response = client.delete("/api/v1/projects/proj-1/clips/clip-1")
    assert response.status_code == 204

    assert await clip_repository.get("clip-1") is None


@pytest.mark.api
async def test_delete_clip_wrong_project(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """Delete clip returns 404 if clip belongs to different project."""
    now = datetime.now(timezone.utc)
    project1 = Project(
        id="proj-1",
        name="Project 1",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    project2 = Project(
        id="proj-2",
        name="Project 2",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project1)
    await project_repository.add(project2)

    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id="video-1",
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    # Try to delete from wrong project
    response = client.delete("/api/v1/projects/proj-2/clips/clip-1")
    assert response.status_code == 404


@pytest.mark.api
async def test_update_clip(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Update clip returns updated data."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    video = make_test_video()
    await video_repository.add(video)

    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    response = client.patch(
        "/api/v1/projects/proj-1/clips/clip-1",
        json={"in_point": 10, "out_point": 150, "timeline_position": 50},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_point"] == 10
    assert data["out_point"] == 150
    assert data["timeline_position"] == 50


@pytest.mark.api
async def test_update_clip_partial(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Update clip with partial data updates only specified fields."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    video = make_test_video()
    await video_repository.add(video)

    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    # Only update timeline_position
    response = client.patch(
        "/api/v1/projects/proj-1/clips/clip-1",
        json={"timeline_position": 500},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_point"] == 0  # Unchanged
    assert data["out_point"] == 100  # Unchanged
    assert data["timeline_position"] == 500  # Updated


@pytest.mark.api
def test_update_clip_not_found(client: TestClient) -> None:
    """Update clip returns 404 for unknown clip."""
    response = client.patch(
        "/api/v1/projects/proj-1/clips/nonexistent",
        json={"in_point": 10},
    )
    assert response.status_code == 404


@pytest.mark.api
async def test_list_clips_with_data(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """List clips returns clips in project."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    video = make_test_video()
    await video_repository.add(video)

    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    response = client.get("/api/v1/projects/proj-1/clips")
    assert response.status_code == 200
    data = response.json()
    assert len(data["clips"]) == 1
    assert data["clips"][0]["id"] == "clip-1"
    assert data["total"] == 1
