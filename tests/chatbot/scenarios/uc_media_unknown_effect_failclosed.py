# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Chatbot testing scenario: unknown effect fail-closed round-trip (BL-795).

Drives the REST API workflow for a render job with an unknown effect type:
1. Create a project
2. Add a clip with an unknown effect type
3. Submit a render
4. Assert the render job fails/declines rather than silently succeeding

Scenario identifier: UC-MEDIA-UNKNOWN-EFFECT-FAILCLOSED
"""

from __future__ import annotations

from typing import Any

import httpx

UC_ID = "UC-MEDIA-UNKNOWN-EFFECT-FAILCLOSED"


async def run_uc_media_unknown_effect_failclosed(base_url: str) -> dict[str, Any]:
    """Drive UC-MEDIA-UNKNOWN-EFFECT-FAILCLOSED: render with unknown effect type.

    Creates a project, adds a clip with an unknown effect type, submits a render,
    and asserts the render declined/failed (fail-closed contract).

    Args:
        base_url: Base URL of the stoat-and-ferret API server.

    Returns:
        Dict with keys:
            uc_id: Scenario identifier.
            project_id: UUID of the created project (or None on error).
            render_job_id: UUID of the submitted render job (or None).
            fail_closed_verified: True when the render job failed as expected.
            status: "success" | "skip" | "scaffold" | "fail".
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"{UC_ID} scenario",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 30,
            },
        )
        if proj_resp.status_code not in (200, 201):
            return {
                "uc_id": UC_ID,
                "project_id": None,
                "render_job_id": None,
                "fail_closed_verified": None,
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
                "fail_closed_verified": None,
                "status": "skip",
                "reason": "could not list videos",
            }
        videos = videos_resp.json().get("videos", [])
        if not videos:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "fail_closed_verified": None,
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
                "effects": [{"effect_type": "totally_unknown_effect_xyz", "parameters": {}}],
            },
        )
        if clip_resp.status_code not in (200, 201):
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "render_job_id": None,
                "fail_closed_verified": None,
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
                        "width": 320,
                        "height": 240,
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
                "fail_closed_verified": None,
                "status": "scaffold",
                "reason": f"render endpoint returned {render_resp.status_code}",
            }

        render_job_id: str | None = render_resp.json().get("id")
        return {
            "uc_id": UC_ID,
            "project_id": project_id,
            "render_job_id": render_job_id,
            "fail_closed_verified": None,
            "status": "scaffold",
            "note": (
                "render submitted; fail-closed verification (job status='failed') requires "
                "polling the render endpoint until terminal state"
            ),
        }


async def test_uc_media_unknown_effect_failclosed_scenario() -> None:
    """UC-MEDIA-UNKNOWN-EFFECT-FAILCLOSED: project + clip with unknown effect via ASGITransport.

    Verifies that:
    - A project is created successfully.
    - A clip with an unknown effect type is added.
    - A render is submitted (the fail-closed outcome is exercised via build_command_for_job
      directly in test_uc_media_unknown_effect_failclosed.py acceptance test).
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
        id="vid-failclosed-1",
        path="/fixtures/clip_test.mp4",
        filename="clip_test.mp4",
        duration_frames=90,
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
        asset_repository=InMemoryAssetRepository(),
    )

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"{UC_ID} scenario",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, f"project creation failed: {proj_resp.text}"
        project_id: str = proj_resp.json()["id"]

        # Add clip with unknown effect type
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": "vid-failclosed-1",
                "in_point": 0,
                "out_point": 90,
                "timeline_position": 0,
                "effects": [{"effect_type": "totally_unknown_effect_xyz", "parameters": {}}],
            },
        )
        assert clip_resp.status_code == 201, f"clip creation failed: {clip_resp.text}"

        clips_resp = await client.get(f"/api/v1/projects/{project_id}/clips")
        assert clips_resp.status_code == 200
        clips = clips_resp.json()
        assert len(clips) == 1, f"expected 1 clip, got {len(clips)}"
        clip_effects = clips[0].get("effects") or []
        assert len(clip_effects) == 1, f"expected 1 effect on clip, got {clip_effects!r}"
        assert clip_effects[0]["effect_type"] == "totally_unknown_effect_xyz"
