# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for clip endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.asset_repository import AssetRecord
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from tests.test_api.conftest import InMemoryAssetRepository
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


@pytest.mark.api
async def test_list_clips_effects_default_empty_list(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Clips with no effects return effects: [] not effects: null."""
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
    clip_data = data["clips"][0]
    assert clip_data["effects"] == []
    assert clip_data["effects"] is not None


@pytest.mark.api
async def test_get_clip_success(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """GET /clips/{cid} returns 200 with ClipResponse when clip exists."""
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

    response = client.get("/api/v1/projects/proj-1/clips/clip-1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "clip-1"
    assert data["project_id"] == "proj-1"
    assert data["source_video_id"] == video.id
    assert data["in_point"] == 0
    assert data["out_point"] == 100
    assert data["effects"] == []


@pytest.mark.api
def test_get_clip_not_found(client: TestClient) -> None:
    """GET /clips/{cid} returns 404 for nonexistent clip."""
    response = client.get("/api/v1/projects/proj-1/clips/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_get_clip_wrong_project(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """GET /clips/{cid} returns 404 when clip belongs to a different project."""
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

    response = client.get("/api/v1/projects/proj-2/clips/clip-1")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_get_clip_effects_empty(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """GET /clips/{cid}/effects returns 200 with empty list when no effects."""
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

    response = client.get("/api/v1/projects/proj-1/clips/clip-1/effects")
    assert response.status_code == 200
    data = response.json()
    assert data["effects"] == []


@pytest.mark.api
def test_get_clip_effects_not_found(client: TestClient) -> None:
    """GET /clips/{cid}/effects returns 404 for nonexistent clip."""
    response = client.get("/api/v1/projects/proj-1/clips/nonexistent/effects")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_add_image_clip_success(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    asset_repository: InMemoryAssetRepository,
) -> None:
    """Image clip with a seeded image asset returns 201."""
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

    now_iso = now.isoformat()
    asset = AssetRecord(
        id="asset-real-img",
        original_filename="test.png",
        content_hash="deadbeef" * 8,
        mime_type="image/png",
        kind="image",
        size_bytes=1024,
        file_path="/tmp/test.png",
        deleted_at=None,
        created_at=now_iso,
        updated_at=now_iso,
    )
    await asset_repository.insert(asset)

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "clip_type": "image",
            "source_asset_id": "asset-real-img",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["clip_type"] == "image"
    assert data["source_asset_id"] == "asset-real-img"
    assert data["source_video_id"] is None


@pytest.mark.api
async def test_add_image_clip_asset_not_found(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Image clip with a non-existent source_asset_id returns 404 ASSET_NOT_FOUND."""
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
            "clip_type": "image",
            "source_asset_id": "asset-does-not-exist",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "ASSET_NOT_FOUND"
    assert "asset-does-not-exist" in data["detail"]["message"]


@pytest.mark.api
async def test_add_image_clip_soft_deleted_asset(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    asset_repository: InMemoryAssetRepository,
) -> None:
    """Image clip referencing a soft-deleted asset returns 404 ASSET_NOT_FOUND."""
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

    now_iso = now.isoformat()
    deleted_asset = AssetRecord(
        id="asset-deleted",
        original_filename="deleted.png",
        content_hash="cafebabe" * 8,
        mime_type="image/png",
        kind="image",
        size_bytes=512,
        file_path="/tmp/deleted.png",
        deleted_at=now_iso,
        created_at=now_iso,
        updated_at=now_iso,
    )
    await asset_repository.insert(deleted_asset)

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "clip_type": "image",
            "source_asset_id": "asset-deleted",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "ASSET_NOT_FOUND"


@pytest.mark.api
async def test_add_image_clip_asset_kind_mismatch(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    asset_repository: InMemoryAssetRepository,
) -> None:
    """Image clip referencing an asset with kind != 'image' returns 422 ASSET_KIND_MISMATCH."""
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

    now_iso = now.isoformat()
    audio_asset = AssetRecord(
        id="asset-audio-1",
        original_filename="track.mp3",
        content_hash="beefdead" * 8,
        mime_type="audio/mpeg",
        kind="audio",
        size_bytes=2048,
        file_path="/tmp/track.mp3",
        deleted_at=None,
        created_at=now_iso,
        updated_at=now_iso,
    )
    await asset_repository.insert(audio_asset)

    response = client.post(
        "/api/v1/projects/proj-1/clips",
        json={
            "clip_type": "image",
            "source_asset_id": "asset-audio-1",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "ASSET_KIND_MISMATCH"
    assert "audio" in data["detail"]["message"]


@pytest.mark.api
async def test_add_image_clip_missing_source_asset_id(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Image clip without source_asset_id returns 422 (FR-002-AC-1)."""
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
            "clip_type": "image",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 422


@pytest.mark.api
async def test_add_image_clip_with_source_video_id_rejected(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Image clip with source_video_id set returns 422 (cross-field rejection)."""
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
            "clip_type": "image",
            "source_asset_id": "asset-abc123",
            "source_video_id": "video-xyz",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
            "timeline_end": 5.0,
        },
    )
    assert response.status_code == 422


@pytest.mark.api
async def test_add_image_clip_missing_timeline_end(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """Image clip without timeline_end returns 422 (FR-003-AC-1)."""
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
            "clip_type": "image",
            "source_asset_id": "asset-abc123",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 422


@pytest.mark.api
async def test_file_clip_regression_guard(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """File clip creation still works after clip_type Literal extension (regression guard)."""
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
            "clip_type": "file",
            "source_video_id": video.id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["clip_type"] == "file"
    assert data["source_video_id"] == video.id
    assert data["source_asset_id"] is None


@pytest.mark.api
async def test_add_image_clip_source_asset_id_not_null_for_non_image(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """File clip with source_asset_id set returns 422 (cross-field rejection)."""
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
            "clip_type": "file",
            "source_video_id": video.id,
            "source_asset_id": "asset-abc123",
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert response.status_code == 422


def test_image_clip_timeline_end_not_greater_than_start() -> None:
    """Image clip with timeline_end <= timeline_start raises ValidationError (BL-663-AC-3)."""
    from pydantic import ValidationError

    from stoat_ferret.api.schemas.clip import ClipCreate

    # timeline_end < timeline_start
    with pytest.raises(ValidationError) as exc_info:
        ClipCreate.model_validate(
            {
                "clip_type": "image",
                "source_asset_id": "asset-123",
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 0,
                "timeline_start": 5.0,
                "timeline_end": 3.0,
            }
        )
    assert "timeline_end must be greater than timeline_start for image clips" in str(exc_info.value)

    # timeline_end == timeline_start (also invalid)
    with pytest.raises(ValidationError):
        ClipCreate.model_validate(
            {
                "clip_type": "image",
                "source_asset_id": "asset-123",
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 0,
                "timeline_start": 5.0,
                "timeline_end": 5.0,
            }
        )


@pytest.mark.api
async def test_get_clip_allow_header(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """405 on /clips/{cid} includes Allow header listing GET, PATCH, DELETE."""
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

    response = client.put("/api/v1/projects/proj-1/clips/clip-1", json={})
    assert response.status_code == 405
    allow = response.headers.get("allow", "")
    assert "GET" in allow
    assert "PATCH" in allow
    assert "DELETE" in allow
