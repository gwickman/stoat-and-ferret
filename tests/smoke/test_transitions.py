"""Smoke tests for transitions (UC-07).

Validates applying a fade transition between two adjacent clips, exercising
the Rust PyO3 xfade filter builder through the full API stack.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import create_project_with_clips, scan_videos_and_wait


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

    # Apply fade transition between the two clips
    resp = await client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip1_id,
            "target_clip_id": clip2_id,
            "transition_type": "xfade",
            "parameters": {
                "transition": "fade",
                "duration": 1.0,
                "offset": 0.0,
            },
        },
    )
    assert resp.status_code == 201
    transition = resp.json()
    assert "xfade" in transition["filter_string"]
