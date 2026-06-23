# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for negative-path error handling across Phase 3 API surfaces.

Validates that validation rules return correct HTTP error codes and meaningful
error details for timeline, audio, batch, and compose endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tests.smoke.conftest import scan_videos_and_wait


async def test_timeline_invalid_track_type(
    smoke_client: httpx.AsyncClient,
) -> None:
    """PUT timeline with invalid track_type returns 422."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Invalid Track Type Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # PUT timeline with invalid track_type (must be video|audio|text)
    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "invalid", "label": "Bad Track"}],
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body


async def test_timeline_nonexistent_track(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST clip to nonexistent track_id returns 404 (TRACK_NOT_FOUND)."""
    client = smoke_client

    # Scan videos and create a project with a clip
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Nonexistent Track Project"},
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

    # Create a timeline so the project has one, but use a fake track_id
    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200

    # POST clip with nonexistent track_id
    fake_track_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip_id,
            "track_id": fake_track_id,
            "timeline_start": 0.0,
            "timeline_end": 3.0,
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "TRACK_NOT_FOUND"


async def test_timeline_nonexistent_clip(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST clip with nonexistent clip_id returns 404."""
    client = smoke_client

    # Create a project and timeline
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Nonexistent Clip Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    track_id = resp.json()["tracks"][0]["id"]

    # POST clip with nonexistent clip_id
    fake_clip_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": fake_clip_id,
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": 3.0,
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "NOT_FOUND"


async def test_audio_empty_tracks(
    smoke_client: httpx.AsyncClient,
) -> None:
    """PUT audio mix with empty tracks returns 422 (INVALID_TRACK_COUNT)."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Empty Audio Tracks Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # PUT audio mix with empty tracks (requires 2-8)
    resp = await client.put(
        f"/api/v1/projects/{project_id}/audio/mix",
        json={
            "tracks": [],
            "master_volume": 1.0,
            "normalize": True,
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_TRACK_COUNT"


async def test_batch_nonexistent_batch(
    smoke_client: httpx.AsyncClient,
) -> None:
    """GET /api/v1/render/batch/{fake_id} with nonexistent batch returns 404."""
    fake_batch_id = str(uuid.uuid4())
    resp = await smoke_client.get(f"/api/v1/render/batch/{fake_batch_id}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "NOT_FOUND"


async def test_compose_insufficient_inputs(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST layout with insufficient clips returns 422 (INSUFFICIENT_INPUTS)."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Insufficient Inputs Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Grid2x2 requires min_inputs=4, provide only 1
    resp = await client.post(
        f"/api/v1/projects/{project_id}/compose/layout",
        json={"preset": "Grid2x2", "input_count": 1},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INSUFFICIENT_INPUTS"


_STUB_VIDEO_ID = "00000000-0000-0000-0000-000000000001"


async def _ensure_stub_video(client: httpx.AsyncClient) -> str:
    """Insert a minimal stub video row and return its ID."""
    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    now_str = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT OR IGNORE INTO videos "
        "(id, path, filename, duration_frames, frame_rate_numerator, frame_rate_denominator, "
        "width, height, video_codec, file_size, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _STUB_VIDEO_ID,
            "/stub/video.mp4",
            "stub.mp4",
            100,
            30,
            1,
            1280,
            720,
            "h264",
            1000,
            now_str,
            now_str,
        ),
    )
    await db.commit()  # type: ignore[union-attr]
    return _STUB_VIDEO_ID


async def test_video_delete_blocked_when_clip_references_it(
    smoke_client: httpx.AsyncClient,
) -> None:
    """DELETE video returns 409 when a clip still references it via FK constraint (BL-413, AC-4)."""
    video_id = await _ensure_stub_video(smoke_client)

    resp = await smoke_client.post("/api/v1/projects", json={"name": "FK Guard Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={"source_video_id": video_id, "in_point": 0, "out_point": 60, "timeline_position": 0},
    )
    assert resp.status_code == 201

    resp = await smoke_client.delete(f"/api/v1/videos/{video_id}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "FK_CONSTRAINT_VIOLATION"
