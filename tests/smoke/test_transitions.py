# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for transitions (UC-07).

Validates applying a fade transition between two adjacent clips, exercising
the Rust PyO3 xfade filter builder through the full API stack.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import (
    create_adjacent_clips_timeline,
    create_project_with_clips,
    place_clips_on_timeline,
    scan_videos_and_wait,
)


@pytest.mark.usefixtures("videos_dir")
async def test_uc07_fade_transition(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Apply a fade transition between two adjacent clips and verify xfade filter."""
    client = smoke_client

    # Scan videos and get two video IDs
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=2")
    videos = resp.json()["videos"]
    assert len(videos) >= 2
    vid1_id = videos[0]["id"]
    vid2_id = videos[1]["id"]

    # Create project with two adjacent clips
    project, clip_responses = await create_project_with_clips(
        client,
        project_name="Transition Smoke Project",
        video_ids=[vid1_id, vid2_id],
        clips=[
            {
                "source_video_id": vid1_id,
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 0,
            },
            {
                "source_video_id": vid2_id,
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 100,
            },
        ],
    )
    project_id = project["id"]
    clip1_id = clip_responses[0]["id"]
    clip2_id = clip_responses[1]["id"]

    # Add clips to a timeline track so the geometric adjacency check passes
    await place_clips_on_timeline(client, project_id, clip1_id, clip2_id)

    # Apply fade transition between the two clips
    resp = await client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip1_id,
            "target_clip_id": clip2_id,
            "transition_type": "fade",
            "parameters": {
                "transition": "fade",
                "duration": 1.0,
                "offset": 0.0,
            },
        },
    )
    assert resp.status_code == 201
    transition = resp.json()
    assert "id" in transition
    assert len(transition["id"]) > 0
    assert "xfade" in transition["filter_string"]


@pytest.mark.usefixtures("videos_dir")
async def test_transition_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Delete a transition via timeline endpoint and verify removal."""
    client = smoke_client
    setup = await create_adjacent_clips_timeline(client, videos_dir)
    project_id = setup["project_id"]

    # Create a transition between the two adjacent clips
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

    # DELETE the transition
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/timeline/transitions/{transition_id}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert "tracks" in data
    assert "duration" in data

    # Verify transition is no longer present via GET
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["project_id"] == project_id


@pytest.mark.usefixtures("videos_dir")
async def test_smoke_transition_endpoint(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Regression guard: POST /effects/transition with transition_type='fade' returns 201.

    Guards BL-846 fix (registry.get replaced by TransitionType.from_str).
    """
    client = smoke_client
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=2")
    videos = resp.json()["videos"]
    assert len(videos) >= 2
    vid1_id = videos[0]["id"]
    vid2_id = videos[1]["id"]

    project, clip_responses = await create_project_with_clips(
        client,
        project_name="Transition Endpoint Smoke",
        video_ids=[vid1_id, vid2_id],
        clips=[
            {
                "source_video_id": vid1_id,
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 0,
            },
            {
                "source_video_id": vid2_id,
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 100,
            },
        ],
    )
    project_id = project["id"]
    clip1_id = clip_responses[0]["id"]
    clip2_id = clip_responses[1]["id"]

    # Add clips to a timeline track so the geometric adjacency check passes
    await place_clips_on_timeline(client, project_id, clip1_id, clip2_id)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip1_id,
            "target_clip_id": clip2_id,
            "transition_type": "fade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert resp.status_code == 201, (
        f"Expected 201 from transition endpoint, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.usefixtures("videos_dir")
async def test_effects_router_transition_create_then_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Create transition via effects router, delete via timeline endpoint."""
    client = smoke_client

    # Scan videos and get two video IDs
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=2")
    videos = resp.json()["videos"]
    assert len(videos) >= 2
    vid1_id = videos[0]["id"]
    vid2_id = videos[1]["id"]

    # Create project with two adjacent clips
    project, clip_responses = await create_project_with_clips(
        client,
        project_name="Effects-Delete Lifecycle Project",
        video_ids=[vid1_id, vid2_id],
        clips=[
            {
                "source_video_id": vid1_id,
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 0,
            },
            {
                "source_video_id": vid2_id,
                "in_point": 0,
                "out_point": 100,
                "timeline_position": 100,
            },
        ],
    )
    project_id = project["id"]
    clip1_id = clip_responses[0]["id"]
    clip2_id = clip_responses[1]["id"]

    # Add clips to a timeline track so the geometric adjacency check passes
    await place_clips_on_timeline(client, project_id, clip1_id, clip2_id)

    # Create transition via effects router
    resp = await client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip1_id,
            "target_clip_id": clip2_id,
            "transition_type": "fade",
            "parameters": {
                "transition": "fade",
                "duration": 1.0,
                "offset": 0.0,
            },
        },
    )
    assert resp.status_code == 201
    transition = resp.json()
    transition_id = transition["id"]
    assert len(transition_id) > 0

    # Delete via timeline endpoint using the effects-router ID
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/timeline/transitions/{transition_id}",
    )
    assert resp.status_code == 200


@pytest.mark.usefixtures("videos_dir")
async def test_smoke_transition_malformed_duration(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /effects/transition with non-numeric duration returns 400 (BL-853 FR-003)."""
    client = smoke_client
    setup = await create_adjacent_clips_timeline(client, videos_dir)
    project_id = setup["project_id"]
    clip_a_id = setup["clip_a_id"]
    clip_b_id = setup["clip_b_id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_a_id,
            "target_clip_id": clip_b_id,
            "transition_type": "fade",
            "parameters": {"duration": "abc"},
        },
    )
    assert resp.status_code == 400


@pytest.mark.usefixtures("videos_dir")
async def test_smoke_transition_duration_out_of_range(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /effects/transition with duration=60.1 returns 400 INVALID_EFFECT_PARAMS (BL-861)."""
    client = smoke_client
    setup = await create_adjacent_clips_timeline(client, videos_dir)
    project_id = setup["project_id"]
    clip_a_id = setup["clip_a_id"]
    clip_b_id = setup["clip_b_id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_a_id,
            "target_clip_id": clip_b_id,
            "transition_type": "fade",
            "parameters": {"duration": 60.1},
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_EFFECT_PARAMS"


@pytest.mark.usefixtures("videos_dir")
async def test_smoke_transition_duration_nan(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /effects/transition with NaN duration returns 400 INVALID_EFFECT_PARAMS (BL-861)."""
    client = smoke_client
    setup = await create_adjacent_clips_timeline(client, videos_dir)
    project_id = setup["project_id"]
    clip_a_id = setup["clip_a_id"]
    clip_b_id = setup["clip_b_id"]

    payload = {
        "source_clip_id": clip_a_id,
        "target_clip_id": clip_b_id,
        "transition_type": "fade",
        "parameters": {"duration": math.nan},
    }
    resp = await client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        content=json.dumps(payload, allow_nan=True).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_EFFECT_PARAMS"
