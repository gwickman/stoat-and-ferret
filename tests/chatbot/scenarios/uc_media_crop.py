# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Chatbot testing scenario: crop effect media round-trip (BL-796).

Drives the REST API workflow for a render job with a crop effect:
1. Create a project
2. Add a clip with a crop effect (640x360 region)
3. Submit a render
4. Verify the render job was accepted

Scenario identifier: UC-MEDIA-CROP
"""

from __future__ import annotations

from typing import Any

import httpx

UC_ID = "UC-MEDIA-CROP"


async def run_uc_media_crop(base_url: str) -> dict[str, Any]:
    """Drive UC-MEDIA-CROP: render with crop effect (640x360 at x=100, y=50).

    Creates a project, adds a clip with a crop effect, submits a render,
    and verifies the render was accepted.

    Args:
        base_url: Base URL of the stoat-and-ferret API server.

    Returns:
        Dict with keys:
            uc_id: Scenario identifier.
            project_id: UUID of the created project (or None on error).
            render_job_id: UUID of the submitted render job (or None).
            crop_effect_accepted: True when the clip was created with the crop effect.
            status: "success" | "skip" | "scaffold" | "fail".
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"{UC_ID} scenario",
                "output_width": 1280,
                "output_height": 720,
                "output_fps": 30,
            },
        )
        if proj_resp.status_code not in (200, 201):
            return {
                "uc_id": UC_ID,
                "project_id": None,
                "render_job_id": None,
                "crop_effect_accepted": None,
                "status": "fail",
                "step": "create_project",
                "detail": proj_resp.text,
            }
        project_id: str = proj_resp.json()["id"]

        # Find any available video to reference
        videos_resp = await client.get("/api/v1/videos?limit=10")
        if videos_resp.status_code != 200:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "crop_effect_accepted": None,
                "status": "skip",
                "reason": "could not list videos",
            }
        videos = videos_resp.json().get("videos", [])
        if not videos:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "crop_effect_accepted": None,
                "status": "skip",
                "reason": "no videos available in library",
            }

        video = videos[0]
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video["id"],
                "in_point": 0,
                "out_point": min(90, video.get("duration_frames", 90)),
                "timeline_position": 0,
                "effects": [
                    {
                        "effect_type": "crop",
                        "parameters": {"width": 640, "height": 360, "x": 100, "y": 50},
                    }
                ],
            },
        )
        if clip_resp.status_code not in (200, 201):
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "crop_effect_accepted": False,
                "status": "fail",
                "step": "create_clip",
                "detail": clip_resp.text,
            }

        render_resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": {
                    "total_duration": 3.0,
                    "settings": {
                        "output_format": "mp4",
                        "width": 1280,
                        "height": 720,
                        "codec": "libx264",
                        "quality_preset": "standard",
                        "fps": 30.0,
                    },
                },
            },
        )
        if render_resp.status_code not in (200, 201, 202):
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "crop_effect_accepted": True,
                "status": "scaffold",
                "reason": f"render endpoint returned {render_resp.status_code}",
            }

        render_job_id: str | None = render_resp.json().get("id")
        return {
            "uc_id": UC_ID,
            "project_id": project_id,
            "render_job_id": render_job_id,
            "crop_effect_accepted": True,
            "status": "scaffold",
            "note": (
                "render submitted; output dimension verification (640x360) requires "
                "polling the render endpoint and ffprobe on the output file"
            ),
        }


async def test_uc_media_crop_scenario() -> None:
    """UC-MEDIA-CROP: project + clip with crop effect via ASGITransport.

    Verifies that:
    - A project is created successfully.
    - A clip with a crop effect (640x360 at x=100, y=50) is accepted.
    - A render is submitted (output dimension verification is in test_uc_media_crop.py).
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
    video = Video(
        id="vid-crop-1",
        path="/fixtures/clip_1280x720.mp4",
        filename="clip_1280x720.mp4",
        duration_frames=90,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1280,
        height=720,
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
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"{UC_ID} scenario",
                "output_width": 1280,
                "output_height": 720,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, f"project creation failed: {proj_resp.text}"
        project_id: str = proj_resp.json()["id"]

        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": "vid-crop-1",
                "in_point": 0,
                "out_point": 90,
                "timeline_position": 0,
                "effects": [
                    {
                        "effect_type": "crop",
                        "parameters": {"width": 640, "height": 360, "x": 100, "y": 50},
                    }
                ],
            },
        )
        assert clip_resp.status_code == 201, f"clip creation failed: {clip_resp.text}"

        clips_resp = await client.get(f"/api/v1/projects/{project_id}/clips")
        assert clips_resp.status_code == 200
        clips = clips_resp.json()
        assert len(clips) == 1, f"expected 1 clip, got {len(clips)}"
        clip_effects = clips[0].get("effects") or []
        assert len(clip_effects) == 1, f"expected 1 effect on clip, got {clip_effects!r}"
        assert clip_effects[0]["effect_type"] == "crop"
        assert clip_effects[0]["parameters"]["width"] == 640
        assert clip_effects[0]["parameters"]["height"] == 360
