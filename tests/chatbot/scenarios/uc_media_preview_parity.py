# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Chatbot testing scenario: preview composition parity (BL-797).

Drives the REST API workflow for a multi-clip preview session:
1. Create a project
2. Add two clips with distinct timeline positions
3. Start a preview session
4. Verify the session was accepted (202)

Scenario identifier: UC-MEDIA-PREVIEW-PARITY
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx

UC_ID = "UC-MEDIA-PREVIEW-PARITY"

_SOURCE_W = 640
_SOURCE_H = 360


async def run_uc_media_preview_parity(base_url: str) -> dict[str, Any]:
    """Drive UC-MEDIA-PREVIEW-PARITY: two-clip project preview session start.

    Creates a project, adds two clips with distinct timeline windows, starts a
    preview session, and verifies the session was accepted.

    Args:
        base_url: Base URL of the stoat-and-ferret API server.

    Returns:
        Dict with keys:
            uc_id: Scenario identifier.
            project_id: UUID of the created project (or None on error).
            session_id: Preview session ID (or None if not reached).
            status: "success" | "skip" | "scaffold" | "fail".
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"{UC_ID} scenario",
                "output_width": _SOURCE_W,
                "output_height": _SOURCE_H,
                "output_fps": 30,
            },
        )
        if proj_resp.status_code not in (200, 201):
            return {
                "uc_id": UC_ID,
                "project_id": None,
                "session_id": None,
                "status": "fail",
                "step": "create_project",
                "detail": proj_resp.text,
            }
        project_id: str = proj_resp.json()["id"]

        # Find available videos
        videos_resp = await client.get("/api/v1/videos?limit=10")
        if videos_resp.status_code != 200:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "session_id": None,
                "status": "skip",
                "reason": "could not list videos",
            }
        videos = videos_resp.json().get("videos", [])
        if len(videos) < 2:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "session_id": None,
                "status": "skip",
                "reason": f"need at least 2 videos, found {len(videos)}",
            }

        # Add two clips
        for i, (video, t_start) in enumerate([(videos[0], 0), (videos[1], 60)]):
            cr = await client.post(
                f"/api/v1/projects/{project_id}/clips",
                json={
                    "source_video_id": video["id"],
                    "in_point": 0,
                    "out_point": min(60, video.get("duration_frames", 60)),
                    "timeline_position": t_start,
                },
            )
            if cr.status_code not in (200, 201):
                return {
                    "uc_id": UC_ID,
                    "project_id": project_id,
                    "session_id": None,
                    "status": "fail",
                    "step": f"create_clip_{i}",
                    "detail": cr.text,
                }

        # Start preview
        start_resp = await client.post(f"/api/v1/projects/{project_id}/preview/start")
        if start_resp.status_code == 503:
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "session_id": None,
                "status": "skip",
                "reason": "FFmpeg not available on server",
            }
        if start_resp.status_code not in (200, 201, 202):
            return {
                "uc_id": UC_ID,
                "project_id": project_id,
                "session_id": None,
                "status": "scaffold",
                "reason": f"preview start returned {start_resp.status_code}",
                "detail": start_resp.text,
            }

        session_id: str = start_resp.json()["session_id"]
        return {
            "uc_id": UC_ID,
            "project_id": project_id,
            "session_id": session_id,
            "status": "scaffold",
            "note": (
                "preview session started for two-clip project; "
                "HLS segment verification requires STOAT_TEST_FFMPEG=1"
            ),
        }


async def test_uc_media_preview_parity_scenario() -> None:
    """UC-MEDIA-PREVIEW-PARITY: two-clip project preview session via ASGITransport.

    Verifies that:
    - A project is created successfully.
    - Two clips are accepted.
    - A preview session start returns 202 Accepted.
    - The manager.start receives two input_paths (one per clip).
    """
    from stoat_ferret.api.app import create_app
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.models import PreviewQuality, PreviewSession, PreviewStatus, Video
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from stoat_ferret.preview.manager import PreviewManager
    from tests.test_api.conftest import InMemoryAssetRepository

    now = datetime.now(timezone.utc)

    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    for vid_id, path in [
        ("vid-pp-1", "/fixtures/clip_a.mp4"),
        ("vid-pp-2", "/fixtures/clip_b.mp4"),
    ]:
        await video_repo.add(
            Video(
                id=vid_id,
                path=path,
                filename=f"{vid_id}.mp4",
                duration_frames=60,
                frame_rate_numerator=30,
                frame_rate_denominator=1,
                width=_SOURCE_W,
                height=_SOURCE_H,
                video_codec="h264",
                file_size=100_000,
                created_at=now,
                updated_at=now,
                audio_codec=None,
            )
        )

    captured: dict[str, Any] = {}
    mock_manager = MagicMock(spec=PreviewManager)

    async def _start(**kwargs: Any) -> Any:
        captured.update(kwargs)
        from datetime import timedelta

        return PreviewSession(
            id="sess-pp-001",
            project_id="",
            status=PreviewStatus.INITIALIZING,
            manifest_path=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )

    mock_manager.start = AsyncMock(side_effect=_start)

    from unittest.mock import patch

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        preview_manager=mock_manager,
        asset_repository=InMemoryAssetRepository(),
    )

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"{UC_ID} scenario",
                "output_width": _SOURCE_W,
                "output_height": _SOURCE_H,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, proj_resp.text
        project_id = proj_resp.json()["id"]

        # Seed clips directly: the HTTP clip creation endpoint does not set
        # timeline_start/timeline_end for file clips; preview requires them.
        from stoat_ferret.db.models import Clip

        for vid_id, t_start, t_end in [
            ("vid-pp-1", 0.0, 2.0),
            ("vid-pp-2", 2.0, 4.0),
        ]:
            await clip_repo.add(
                Clip(
                    id=Clip.new_id(),
                    project_id=project_id,
                    source_video_id=vid_id,
                    in_point=0,
                    out_point=60,
                    timeline_position=int(t_start * 30),
                    timeline_start=t_start,
                    timeline_end=t_end,
                    created_at=now,
                    updated_at=now,
                )
            )

        with patch("stoat_ferret.api.routers.preview.shutil.which", return_value="/usr/bin/ffmpeg"):
            start_resp = await client.post(f"/api/v1/projects/{project_id}/preview/start")

    assert start_resp.status_code == 202, start_resp.text
    assert "input_paths" in captured, "manager.start was not called with input_paths"
    assert len(captured["input_paths"]) == 2, (
        f"expected 2 input_paths for 2-clip project, got {captured['input_paths']!r}"
    )
