"""Smoke tests for timeline CRUD operations.

Validates creating a timeline with tracks, adding clips to tracks,
and retrieving the full timeline through the HTTP stack with real Rust core.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import scan_videos_and_wait


@pytest.mark.usefixtures("videos_dir")
async def test_timeline_create_add_clip_retrieve(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Create a timeline, add a clip to a track, and retrieve the timeline."""
    client = smoke_client

    # Scan videos to get real metadata
    await scan_videos_and_wait(client, videos_dir)

    # Pick a video
    resp = await client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video = resp.json()["videos"][0]
    video_id = video["id"]

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Timeline Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Add a clip to the project
    resp = await client.post(
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

    # PUT timeline with a video track
    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["project_id"] == project_id
    assert len(timeline["tracks"]) == 1
    track_id = timeline["tracks"][0]["id"]

    # Add clip to the timeline track
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip_id,
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": 3.33,
        },
    )
    assert resp.status_code == 201
    tl_clip = resp.json()
    assert tl_clip["track_id"] == track_id
    assert tl_clip["timeline_start"] == 0.0
    assert tl_clip["timeline_end"] == 3.33

    # GET timeline and verify clip is present
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["project_id"] == project_id
    assert len(timeline["tracks"]) == 1
    track = timeline["tracks"][0]
    assert len(track["clips"]) == 1
    assert track["clips"][0]["id"] == clip_id
    assert timeline["duration"] == pytest.approx(3.33)
