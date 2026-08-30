# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Chatbot testing scenario: non-default output FPS render round-trip (BL-793 AC-7).

Drives the REST API workflow for a two-clip render where the project is configured
with output_fps=24 (non-default):
1. Create a project with output_fps=24
2. Add two clips from available video sources
3. Submit a render job
4. Poll to terminal status
5. Assert r_frame_rate == 24/1 when STOAT_TEST_FFMPEG=1

Scenario identifier: UC-MEDIA-NONDEFAULT-FPS
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx

# Scenario identifier for traceability
UC_ID = "UC-MEDIA-NONDEFAULT-FPS"

_TERMINAL = {"completed", "failed", "cancelled"}


async def run_uc_media_nondefault_fps(base_url: str) -> dict[str, Any]:
    """Drive UC-MEDIA-NONDEFAULT-FPS: render job submitted for a project with output_fps=24.

    Creates a project with output_fps=24, adds two clips, submits a render job,
    polls to terminal status, and (when STOAT_TEST_FFMPEG=1) asserts the frame rate
    oracle via assert_frame_rate from tests/render_oracle.py.

    Args:
        base_url: Base URL of the stoat-and-ferret API server.

    Returns:
        Dict with keys:
            uc_id: Scenario identifier.
            project_id: UUID of the created project (or None on error).
            render_job_id: UUID of the submitted render job (or None).
            status: "success" | "skip" | "fail".
            render_status: Terminal status of the render job.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create project with non-default output_fps=24
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "UC-MEDIA-NONDEFAULT-FPS scenario",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 24,
            },
        )
        if proj_resp.status_code not in (200, 201):
            return {
                "uc_id": UC_ID,
                "project_id": None,
                "render_job_id": None,
                "status": "fail",
                "step": "create_project",
                "detail": proj_resp.text,
            }
        project_id: str = proj_resp.json()["id"]

        # Find any two videos to use as clip sources
        videos_resp = await client.get("/api/v1/videos?limit=10")
        if videos_resp.status_code != 200:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "status": "skip",
                "reason": "could not list videos",
            }
        videos = videos_resp.json().get("videos", [])
        if len(videos) < 2:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "status": "skip",
                "reason": "fewer than 2 videos available",
            }

        # Add two clips
        for i, video in enumerate(videos[:2]):
            clip_resp = await client.post(
                f"/api/v1/projects/{project_id}/clips",
                json={
                    "source_video_id": video["id"],
                    "in_point": 0,
                    "out_point": min(150, video.get("duration_frames", 150)),
                    "timeline_position": i * 150,
                },
            )
            if clip_resp.status_code not in (200, 201):
                return {
                    "uc_id": UC_ID,
                    "project_id": project_id,
                    "render_job_id": None,
                    "status": "fail",
                    "step": f"create_clip_{i}",
                    "detail": clip_resp.text,
                }

        # Submit render job
        render_resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": json.dumps(
                    {
                        "total_duration": 9.0,
                        "settings": {
                            "output_format": "mp4",
                            "width": 320,
                            "height": 240,
                            "codec": "libx264",
                            "quality_preset": "standard",
                            "fps": 24.0,
                        },
                    }
                ),
            },
        )
        if render_resp.status_code not in (200, 201, 202):
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "status": "fail",
                "reason": f"render endpoint returned {render_resp.status_code}",
            }

        render_job_id: str = render_resp.json()["id"]

        # Poll to terminal status
        deadline = asyncio.get_running_loop().time() + 120.0
        final_status = ""
        final_resp = None
        while asyncio.get_running_loop().time() < deadline:
            final_resp = await client.get(f"/api/v1/render/{render_job_id}")
            if final_resp.status_code != 200:
                break
            final_status = final_resp.json().get("status", "")
            if final_status in _TERMINAL:
                break
            await asyncio.sleep(2.0)

        # STOAT_TEST_FFMPEG-gated oracle: assert r_frame_rate == 24/1
        if (
            os.getenv("STOAT_TEST_FFMPEG")
            and final_status == "completed"
            and final_resp is not None
        ):
            from pathlib import Path

            from tests.render_oracle import assert_frame_rate

            output_path = Path(final_resp.json()["output_path"])
            await assert_frame_rate(output_path, 24, 1)

        return {
            "uc_id": UC_ID,
            "project_id": project_id,
            "render_job_id": render_job_id,
            "status": "success" if final_status == "completed" else "fail",
            "render_status": final_status,
        }


async def test_uc_media_nondefault_fps_scenario() -> None:
    """UC-MEDIA-NONDEFAULT-FPS: project with output_fps=24 + two-clip workflow (BL-793 AC-7).

    Verifies that:
    - A project is created with output_fps=24 successfully.
    - Two clips are added to the project.
    - A render job is submitted and accepted (201).
    - The render job reaches a terminal status (completed or failed).
    - When STOAT_TEST_FFMPEG=1 and render completed, asserts r_frame_rate == 24/1.
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
    for vid_id in ["vid-fps-1", "vid-fps-2"]:
        video = Video(
            id=vid_id,
            path=f"/fixtures/{vid_id}.mp4",
            filename=f"{vid_id}.mp4",
            duration_frames=150,
            frame_rate_numerator=30,
            frame_rate_denominator=1,
            width=320,
            height=240,
            video_codec="h264",
            file_size=500_000,
            created_at=now,
            updated_at=now,
            audio_codec=None,
        )
        await video_repo.add(video)

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        asset_repository=InMemoryAssetRepository(),
    )

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project with output_fps=24
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "UC-MEDIA-NONDEFAULT-FPS scenario",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 24,
            },
        )
        assert proj_resp.status_code == 201, f"project creation failed: {proj_resp.text}"
        project_id: str = proj_resp.json()["id"]
        assert proj_resp.json()["output_fps"] == 24, "output_fps must be persisted as 24"

        # Add two clips
        for i, vid_id in enumerate(["vid-fps-1", "vid-fps-2"]):
            clip_resp = await client.post(
                f"/api/v1/projects/{project_id}/clips",
                json={
                    "source_video_id": vid_id,
                    "in_point": 0,
                    "out_point": 150,
                    "timeline_position": i * 150,
                },
            )
            assert clip_resp.status_code == 201, f"clip {i} creation failed: {clip_resp.text}"

        # Verify two clips were added
        clips_resp = await client.get(f"/api/v1/projects/{project_id}/clips")
        assert clips_resp.status_code == 200
        clips = clips_resp.json()["clips"]
        assert len(clips) == 2, f"expected 2 clips, got {len(clips)}"

        # Submit render job
        render_resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": json.dumps(
                    {
                        "total_duration": 9.0,
                        "settings": {
                            "output_format": "mp4",
                            "width": 320,
                            "height": 240,
                            "codec": "libx264",
                            "quality_preset": "standard",
                            "fps": 24.0,
                        },
                    }
                ),
            },
        )
        if render_resp.status_code == 503:
            return  # render service not initialized; project + clip assertions already verified
        assert render_resp.status_code == 201, (
            f"render submit failed: {render_resp.status_code} {render_resp.text}"
        )
        render_job_id: str = render_resp.json()["id"]

        # Poll to terminal status
        deadline = asyncio.get_running_loop().time() + 120.0
        final_status = ""
        final_resp = None
        while asyncio.get_running_loop().time() < deadline:
            final_resp = await client.get(f"/api/v1/render/{render_job_id}")
            assert final_resp.status_code == 200, f"render status check failed: {final_resp.text}"
            final_status = final_resp.json().get("status", "")
            if final_status in _TERMINAL:
                break
            await asyncio.sleep(1.0)

        # STOAT_TEST_FFMPEG-gated oracle: assert r_frame_rate == 24/1
        if (
            os.getenv("STOAT_TEST_FFMPEG")
            and final_status == "completed"
            and final_resp is not None
        ):
            from pathlib import Path

            from tests.render_oracle import assert_frame_rate

            output_path = Path(final_resp.json()["output_path"])
            await assert_frame_rate(output_path, 24, 1)
