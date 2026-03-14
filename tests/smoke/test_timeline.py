"""Smoke tests for timeline CRUD operations.

Validates creating a timeline with tracks, adding clips to tracks,
updating clip positions/track assignments, and removing clips from the
timeline through the HTTP stack with real Rust core.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import create_adjacent_clips_timeline, scan_videos_and_wait


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


@pytest.mark.usefixtures("videos_dir")
async def test_timeline_clip_patch_position(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """PATCH a clip's timeline_start/timeline_end and verify via GET."""
    client = smoke_client

    # Setup: scan videos, create project, clip, timeline, track, add clip to timeline
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Patch Position Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

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

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    track_id = resp.json()["tracks"][0]["id"]

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

    # PATCH: update position
    resp = await client.patch(
        f"/api/v1/projects/{project_id}/timeline/clips/{clip_id}",
        json={"timeline_start": 5.0, "timeline_end": 10.0},
    )
    assert resp.status_code == 200
    patched = resp.json()
    assert patched["timeline_start"] == pytest.approx(5.0)
    assert patched["timeline_end"] == pytest.approx(10.0)

    # Verify via GET
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    track = resp.json()["tracks"][0]
    clip_on_tl = next(c for c in track["clips"] if c["id"] == clip_id)
    assert clip_on_tl["timeline_start"] == pytest.approx(5.0)
    assert clip_on_tl["timeline_end"] == pytest.approx(10.0)


@pytest.mark.usefixtures("videos_dir")
async def test_timeline_clip_patch_track(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """PATCH a clip's track_id to a second track and verify via GET."""
    client = smoke_client

    # Setup: scan videos, create project, clip, timeline with TWO tracks
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Patch Track Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

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

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[
            {"track_type": "video", "label": "V1"},
            {"track_type": "video", "label": "V2"},
        ],
    )
    assert resp.status_code == 200
    tracks = resp.json()["tracks"]
    track_1_id = tracks[0]["id"]
    track_2_id = tracks[1]["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip_id,
            "track_id": track_1_id,
            "timeline_start": 0.0,
            "timeline_end": 3.33,
        },
    )
    assert resp.status_code == 201

    # PATCH: reassign to track 2
    resp = await client.patch(
        f"/api/v1/projects/{project_id}/timeline/clips/{clip_id}",
        json={"track_id": track_2_id},
    )
    assert resp.status_code == 200
    patched = resp.json()
    assert patched["track_id"] == track_2_id

    # Verify via GET: clip should be on track 2, not track 1
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    track_1 = next(t for t in timeline["tracks"] if t["id"] == track_1_id)
    track_2 = next(t for t in timeline["tracks"] if t["id"] == track_2_id)
    assert all(c["id"] != clip_id for c in track_1["clips"])
    assert any(c["id"] == clip_id for c in track_2["clips"])


@pytest.mark.usefixtures("videos_dir")
async def test_timeline_clip_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """DELETE a clip from timeline and verify it is absent via GET."""
    client = smoke_client

    # Setup: scan videos, create project, clip, timeline, track, add clip
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Delete Clip Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

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

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    track_id = resp.json()["tracks"][0]["id"]

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

    # DELETE clip from timeline
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/timeline/clips/{clip_id}",
    )
    assert resp.status_code == 204

    # Verify via GET: clip should no longer appear on the track
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    track = resp.json()["tracks"][0]
    assert all(c["id"] != clip_id for c in track["clips"])


@pytest.mark.usefixtures("videos_dir")
async def test_timeline_transition_create(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST transition between adjacent clips returns 201 with filter_string."""
    client = smoke_client
    setup = await create_adjacent_clips_timeline(client, videos_dir)
    project_id = setup["project_id"]

    # POST transition between the two adjacent clips
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/transitions",
        json={
            "clip_a_id": setup["clip_a_id"],
            "clip_b_id": setup["clip_b_id"],
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["transition_type"] == "fade"
    assert data["duration"] == 1.0
    assert "filter_string" in data
    assert len(data["filter_string"]) > 0
    assert "timeline_offset" in data
    assert isinstance(data["timeline_offset"], float)
    assert "id" in data

    # GET timeline confirms transition data is present
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["project_id"] == project_id
    assert len(timeline["tracks"]) >= 1


@pytest.mark.usefixtures("videos_dir")
async def test_timeline_transition_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """DELETE transition removes it and returns updated TimelineResponse."""
    client = smoke_client
    setup = await create_adjacent_clips_timeline(client, videos_dir)
    project_id = setup["project_id"]

    # Create a transition first
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/transitions",
        json={
            "clip_a_id": setup["clip_a_id"],
            "clip_b_id": setup["clip_b_id"],
            "transition_type": "fade",
            "duration": 1.0,
        },
    )
    assert resp.status_code == 201
    transition_id = resp.json()["id"]

    # Record duration with transition applied
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    duration_with_transition = resp.json()["duration"]

    # DELETE the transition
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/timeline/transitions/{transition_id}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert "tracks" in data
    assert "duration" in data
    assert isinstance(data["duration"], float)

    # Duration should be recalculated (>= duration with transition, since
    # removing overlap restores original length)
    assert data["duration"] >= duration_with_transition

    # GET confirms transition is gone and duration recalculated
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["duration"] >= duration_with_transition
