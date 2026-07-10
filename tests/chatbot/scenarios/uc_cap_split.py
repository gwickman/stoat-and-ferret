# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Chatbot scenario: uc_cap_split — split a clip at the current playhead frame.

Exercises the full HTTP path:
  POST /api/v1/projects
  POST /api/v1/projects/{id}/clips
  POST /api/v1/projects/{id}/clips/{id}/split
  Asserts clip_a.out_point == split_frame and clip_b.in_point == split_frame.
"""

from __future__ import annotations

from typing import Any

import httpx


async def run_uc_cap_split(base_url: str) -> dict[str, Any]:
    """Run the clip-split chatbot capability scenario.

    Creates a project and clip, splits the clip at a given frame, and
    verifies the resulting clips have correct in/out points.

    Args:
        base_url: Base URL of the running API server (e.g. 'http://127.0.0.1:8765').

    Returns:
        Dict with 'status' ('ok', 'skip', or 'fail') and diagnostic detail.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "uc_cap_split scenario",
                "output_width": 1920,
                "output_height": 1080,
                "output_fps": 30,
            },
        )
        if proj_resp.status_code != 201:
            return {"status": "fail", "step": "create_project", "detail": proj_resp.json()}
        project_id = proj_resp.json()["id"]

        # List videos to find a usable source
        videos_resp = await client.get("/api/v1/videos?limit=1")
        if videos_resp.status_code != 200 or not videos_resp.json().get("videos"):
            return {"status": "skip", "reason": "no videos available for scenario"}
        video_id = videos_resp.json()["videos"][0]["id"]

        # Create a clip with 120 frames (4s at 30fps)
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video_id,
                "in_point": 0,
                "out_point": 120,
                "timeline_position": 0,
            },
        )
        if clip_resp.status_code != 201:
            return {"status": "fail", "step": "create_clip", "detail": clip_resp.json()}
        clip_id = clip_resp.json()["id"]

        # Split the clip at frame 60
        split_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/split",
            json={"split_frame": 60},
        )
        if split_resp.status_code != 200:
            return {"status": "fail", "step": "split_clip", "detail": split_resp.json()}

        split_data = split_resp.json()
        clip_a = split_data["clip_a"]
        clip_b = split_data["clip_b"]

        # Verify adjacent in/out points
        if clip_a["out_point"] != 60:
            return {
                "status": "fail",
                "step": "verify_clip_a_out_point",
                "detail": f"expected clip_a.out_point=60, got {clip_a['out_point']}",
            }
        if clip_b["in_point"] != 60:
            return {
                "status": "fail",
                "step": "verify_clip_b_in_point",
                "detail": f"expected clip_b.in_point=60, got {clip_b['in_point']}",
            }

        # Verify total coverage preserved
        if clip_a["in_point"] != 0:
            return {
                "status": "fail",
                "step": "verify_clip_a_in_point",
                "detail": f"expected clip_a.in_point=0, got {clip_a['in_point']}",
            }
        if clip_b["out_point"] != 120:
            return {
                "status": "fail",
                "step": "verify_clip_b_out_point",
                "detail": f"expected clip_b.out_point=120, got {clip_b['out_point']}",
            }

    return {
        "status": "ok",
        "clip_a_id": clip_a["id"],
        "clip_b_id": clip_b["id"],
        "split_frame": 60,
    }


async def test_uc_cap_split_scenario() -> None:
    """FR-004-AC-1: chatbot scenario drives split via httpx.AsyncClient in-process.

    Uses ASGITransport to run the scenario against the real FastAPI app without
    a live server.
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
    # Seed a video so the scenario can create a clip
    video = Video(
        id="vid-1",
        path="/test/video.mp4",
        filename="video.mp4",
        duration_frames=300,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=1000,
        created_at=now,
        updated_at=now,
    )
    await video_repo.add(video)

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        asset_repository=InMemoryAssetRepository(),  # BL-633: DI mode needs explicit injection
    )

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "uc_cap_split scenario",
                "output_width": 1920,
                "output_height": 1080,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        # Create clip (ASGITransport: no live video validation path, use seeded video)
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": "vid-1",
                "in_point": 0,
                "out_point": 120,
                "timeline_position": 0,
            },
        )
        assert clip_resp.status_code == 201
        clip_id = clip_resp.json()["id"]

        # Split at frame 60
        split_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/split",
            json={"split_frame": 60},
        )
        assert split_resp.status_code == 200
        split_data = split_resp.json()

        clip_a = split_data["clip_a"]
        clip_b = split_data["clip_b"]

        assert clip_a["out_point"] == 60, (
            f"clip_a.out_point should be 60, got {clip_a['out_point']}"
        )
        assert clip_b["in_point"] == 60, f"clip_b.in_point should be 60, got {clip_b['in_point']}"
        assert clip_a["in_point"] == 0
        assert clip_b["out_point"] == 120
        assert clip_a["effects"] == []
        assert clip_b["effects"] == []
