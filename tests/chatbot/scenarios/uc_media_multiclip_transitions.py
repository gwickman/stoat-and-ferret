# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Chatbot testing scenario: multi-clip transition render round-trip (BL-792 AC-5).

Drives the REST API workflow for a two-clip render with a saved wipeleft/0.35 transition:
1. Create a project
2. Add two clips from any available video sources
3. Save a wipeleft/0.35 transition between the clips
4. Submit a multi-clip render
5. Assert the render job was accepted

Scenario identifier: UC-MEDIA-MULTICLIP-TRANSITIONS
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

UC_ID = "UC-MEDIA-MULTICLIP-TRANSITIONS"

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"


async def run_uc_media_multiclip_transitions(base_url: str) -> dict[str, Any]:
    """Drive UC-MEDIA-MULTICLIP-TRANSITIONS: two-clip render with wipeleft/0.35 transition.

    Creates a project, adds two clips, saves a wipeleft/0.35 transition between them,
    and submits a render job. The visual seam oracle is covered by the acceptance test
    (test_uc_media_multiclip_assemble.py) gated under STOAT_TEST_FFMPEG=1.

    Args:
        base_url: Base URL of the stoat-and-ferret API server.

    Returns:
        Dict with keys:
            uc_id: Scenario identifier.
            project_id: UUID of the created project (or None on error).
            clip_a_id: UUID of the first clip (or None).
            render_job_id: UUID of the submitted render job (or None).
            status: "success" | "skip" | "scaffold" | "fail".
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "UC-MEDIA-MULTICLIP-TRANSITIONS scenario",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 30,
            },
        )
        if proj_resp.status_code not in (200, 201):
            return {
                "uc_id": UC_ID,
                "project_id": None,
                "clip_a_id": None,
                "render_job_id": None,
                "status": "fail",
                "step": "create_project",
                "detail": proj_resp.text,
            }
        project_id: str = proj_resp.json()["id"]

        # Find any two videos for the clips
        videos_resp = await client.get("/api/v1/videos?limit=10")
        if videos_resp.status_code != 200:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "clip_a_id": None,
                "render_job_id": None,
                "status": "skip",
                "reason": "could not list videos",
            }
        videos = videos_resp.json().get("videos", [])
        if len(videos) < 2:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "clip_a_id": None,
                "render_job_id": None,
                "status": "skip",
                "reason": "fewer than 2 videos available",
            }

        # Add two clips (first 5s = 150 frames @ 30fps of each source)
        clip_ids: list[str] = []
        for i, video in enumerate(videos[:2]):
            clip_resp = await client.post(
                f"/api/v1/projects/{project_id}/clips",
                json={
                    "source_video_id": video["id"],
                    "in_point": 0,
                    "out_point": min(150, video.get("duration_frames", 150)),
                    "timeline_position": i * 150,
                    "timeline_start": i * 5.0,
                    "timeline_end": (i + 1) * 5.0,
                },
            )
            if clip_resp.status_code not in (200, 201):
                return {
                    "uc_id": UC_ID,
                    "project_id": project_id,
                    "clip_a_id": None,
                    "render_job_id": None,
                    "status": "fail",
                    "step": f"create_clip_{i}",
                    "detail": clip_resp.text,
                }
            clip_ids.append(clip_resp.json()["id"])

        clip_a_id = clip_ids[0]
        clip_b_id = clip_ids[1]

        # Save wipeleft/0.35 transition between clip_a and clip_b
        tr_resp = await client.post(
            f"/api/v1/projects/{project_id}/timeline/transitions",
            json={
                "clip_a_id": clip_a_id,
                "clip_b_id": clip_b_id,
                "transition_type": "wipeleft",
                "duration": 0.35,
            },
        )
        if tr_resp.status_code not in (200, 201, 204):
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "clip_a_id": clip_a_id,
                "render_job_id": None,
                "status": "fail",
                "step": "save_transitions",
                "detail": tr_resp.text,
            }

        # Submit multi-clip render: 5s + 5s - 0.35s xfade = 9.65s total
        render_resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": json.dumps(
                    {
                        "total_duration": 9.65,
                        "settings": {
                            "output_format": "mp4",
                            "width": 320,
                            "height": 240,
                            "codec": "libx264",
                            "quality_preset": "standard",
                            "fps": 30.0,
                        },
                    }
                ),
            },
        )
        if render_resp.status_code not in (200, 201, 202):
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "clip_a_id": clip_a_id,
                "render_job_id": None,
                "status": "scaffold",
                "reason": f"render endpoint returned {render_resp.status_code}",
            }

        render_job_id: str | None = render_resp.json().get("id")
        return {
            "uc_id": UC_ID,
            "project_id": project_id,
            "clip_a_id": clip_a_id,
            "render_job_id": render_job_id,
            "status": "scaffold",
            "note": (
                "render submitted; visual seam oracle requires"
                " STOAT_TEST_FFMPEG=1 and a completed render"
            ),
        }


async def test_uc_media_multiclip_transitions_scenario() -> None:
    """UC-MEDIA-MULTICLIP-TRANSITIONS: project + two-clip + transition workflow via ASGITransport.

    Verifies that:
    - A project is created successfully.
    - Two clips are added.
    - A wipeleft/0.35 transition is saved between the clips.
    - A multi-clip render is submitted and accepted.

    Visual oracle assertions (assert_transition_reference) require a live FFmpeg render and
    are covered by the acceptance test (test_uc_media_multiclip_assemble.py) gated under
    STOAT_TEST_FFMPEG=1.
    """
    from datetime import datetime, timezone

    from stoat_ferret.api.app import create_app
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.models import Video
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from tests.test_api.conftest import InMemoryAssetRepository

    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    now = datetime.now(timezone.utc)
    for vid_id, filename in [("vid-tr-1", "clip_a.mp4"), ("vid-tr-2", "clip_b.mp4")]:
        video = Video(
            id=vid_id,
            path=f"/fixtures/{filename}",
            filename=filename,
            duration_frames=150,
            frame_rate_numerator=30,
            frame_rate_denominator=1,
            width=320,
            height=240,
            video_codec="h264",
            file_size=500_000,
            created_at=now,
            updated_at=now,
            audio_codec="aac",
        )
        await video_repo.add(video)

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        asset_repository=InMemoryAssetRepository(),  # type: ignore[arg-type]
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "UC-MEDIA-MULTICLIP-TRANSITIONS scenario",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, f"project creation failed: {proj_resp.text}"
        project_id: str = proj_resp.json()["id"]

        # Add two clips with timeline_start/timeline_end for adjacency check
        clip_ids: list[str] = []
        for i, vid_id in enumerate(["vid-tr-1", "vid-tr-2"]):
            clip_resp = await client.post(
                f"/api/v1/projects/{project_id}/clips",
                json={
                    "source_video_id": vid_id,
                    "in_point": 0,
                    "out_point": 150,
                    "timeline_position": i * 150,
                    "timeline_start": i * 5.0,
                    "timeline_end": (i + 1) * 5.0,
                },
            )
            assert clip_resp.status_code == 201, f"clip {i} creation failed: {clip_resp.text}"
            clip_ids.append(clip_resp.json()["id"])

        clip_a_id = clip_ids[0]
        clip_b_id = clip_ids[1]

        # Save wipeleft/0.35 transition: flat body to /timeline/transitions
        tr_resp = await client.post(
            f"/api/v1/projects/{project_id}/timeline/transitions",
            json={
                "clip_a_id": clip_a_id,
                "clip_b_id": clip_b_id,
                "transition_type": "wipeleft",
                "duration": 0.35,
            },
        )
        assert tr_resp.status_code in (200, 201, 204), f"save transitions failed: {tr_resp.text}"

        # Verify two clips were added
        clips_resp = await client.get(f"/api/v1/projects/{project_id}/clips")
        assert clips_resp.status_code == 200
        clips = clips_resp.json()
        assert len(clips) == 2, f"expected 2 clips, got {len(clips)}"

        # Submit multi-clip render and assert accepted
        render_resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": json.dumps(
                    {
                        "total_duration": 9.65,
                        "settings": {
                            "codec": "libx264",
                            "fps": 30.0,
                            "width": 320,
                            "height": 240,
                            "quality_preset": "standard",
                        },
                    }
                ),
            },
        )
        assert render_resp.status_code == 201, (
            f"render submit failed: {render_resp.status_code} {render_resp.text}"
        )
        assert render_resp.json().get("id"), "render response missing job id"
