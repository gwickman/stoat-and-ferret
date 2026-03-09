"""Smoke tests for clip management (UC-04) and clip modification (UC-10).

Validates adding, listing, modifying, and deleting clips through the full
backend stack with real scanned video metadata.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import EXPECTED_VIDEOS, scan_videos_and_wait


@pytest.mark.usefixtures("videos_dir")
async def test_uc04_add_clips(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Add clips to a project and verify validation rejects invalid out_points."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Pick a video to use for clips
    resp = await smoke_client.get("/api/v1/videos?limit=100")
    videos = resp.json()["videos"]
    by_name = {v["filename"]: v for v in videos}

    video = by_name["running1.mp4"]
    video_id = video["id"]
    expected = EXPECTED_VIDEOS["running1.mp4"]

    # Create a project
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Clip Test Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Add two clips with valid in/out points
    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201
    clip1 = resp.json()

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 200,
            "out_point": 400,
            "timeline_position": 100,
        },
    )
    assert resp.status_code == 201
    clip2 = resp.json()

    # List clips — both should be present
    resp = await smoke_client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    clip_ids = {c["id"] for c in body["clips"]}
    assert clip1["id"] in clip_ids
    assert clip2["id"] in clip_ids

    # Validation: out_point beyond video duration returns 400
    beyond_duration = expected["frames"] + 100
    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": beyond_duration,
            "timeline_position": 200,
        },
    )
    assert resp.status_code == 400


@pytest.mark.usefixtures("videos_dir")
async def test_uc10_modify_clips(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Modify clip properties and delete a clip."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Get a video
    resp = await smoke_client.get("/api/v1/videos?limit=1")
    video = resp.json()["videos"][0]
    video_id = video["id"]

    # Create project and add a clip
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Modify Clip Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201
    clip_id = resp.json()["id"]

    # PATCH to update in/out points
    resp = await smoke_client.patch(
        f"/api/v1/projects/{project_id}/clips/{clip_id}",
        json={"in_point": 10, "out_point": 200},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["in_point"] == 10
    assert updated["out_point"] == 200

    # PATCH to update timeline position
    resp = await smoke_client.patch(
        f"/api/v1/projects/{project_id}/clips/{clip_id}",
        json={"timeline_position": 50},
    )
    assert resp.status_code == 200
    assert resp.json()["timeline_position"] == 50

    # DELETE clip
    resp = await smoke_client.delete(
        f"/api/v1/projects/{project_id}/clips/{clip_id}",
    )
    assert resp.status_code == 204

    # GET clips returns empty list
    resp = await smoke_client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["clips"] == []
