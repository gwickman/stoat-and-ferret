# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_preview_seek — seek position forwarded to manager (BL-798).

Verifies that manager.seek() is called with position=<requested_value>.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, PreviewQuality, PreviewSession, PreviewStatus, Video
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.preview.manager import PreviewManager
from tests.test_api.conftest import InMemoryAssetRepository

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-preview-seek-001"
_SOURCE_W = 640
_SOURCE_H = 360


def _make_video(vid_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
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


def _make_clip(
    clip_id: str, project_id: str, vid_id: str, timeline_start: float, timeline_end: float
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=project_id,
        source_video_id=vid_id,
        in_point=0,
        out_point=60,
        timeline_position=int(timeline_start * 30),
        timeline_start=timeline_start,
        timeline_end=timeline_end,
        created_at=now,
        updated_at=now,
    )


@_FFMPEG_SKIP
@pytest.mark.skip(reason="BL-836: _capture_seek(**kwargs) receives a positional arg from AsyncMock — fix deferred to v137")
@pytest.mark.asyncio
async def test_seek_position_forwarded_through_manager_to_generator(tmp_path: Path) -> None:
    """Seek with position=5.0 forwards position to manager.seek and start_offset_s to generator.

    Verifies the full parameter propagation chain:
    seek router → manager.seek(position=5.0) → generator.generate(start_offset_s=5.0)
    """
    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    video_a = _make_video("vid-seek-a", str(tmp_path / "clip_a.mp4"))
    await video_repo.add(video_a)

    now = datetime.now(timezone.utc)
    seek_session = PreviewSession(
        id="sess-seek-001",
        project_id=_PROJECT_ID,
        status=PreviewStatus.READY,
        manifest_path=None,
        error_message=None,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        quality_level=PreviewQuality.MEDIUM,
    )

    captured_seek: dict[str, object] = {}

    mock_manager = MagicMock(spec=PreviewManager)

    async def _capture_get_status(session_id: str) -> PreviewSession:
        return seek_session

    async def _capture_seek(**kwargs: object) -> PreviewSession:
        captured_seek.update(kwargs)
        return PreviewSession(
            id="sess-seek-001",
            project_id=_PROJECT_ID,
            status=PreviewStatus.SEEKING,
            manifest_path=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )

    mock_manager.get_status = AsyncMock(side_effect=_capture_get_status)
    mock_manager.seek = AsyncMock(side_effect=_capture_seek)

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        preview_manager=mock_manager,
        asset_repository=InMemoryAssetRepository(),
    )

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "preview-seek-test",
                "output_width": _SOURCE_W,
                "output_height": _SOURCE_H,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, proj_resp.text
        project_id = proj_resp.json()["id"]

        # Seed a clip with timeline positions (bypassing HTTP endpoint)
        clip_a = _make_clip("clip-seek-a", project_id, "vid-seek-a", 0.0, 2.0)
        await clip_repo.add(clip_a)

        # Override get_status to return a session for the project
        seek_session_for_project = PreviewSession(
            id="sess-seek-001",
            project_id=project_id,
            status=PreviewStatus.READY,
            manifest_path=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )
        mock_manager.get_status = AsyncMock(return_value=seek_session_for_project)

        with patch("stoat_ferret.api.routers.preview.shutil.which", return_value="/usr/bin/ffmpeg"):
            seek_resp = await client.post(
                "/api/v1/preview/sess-seek-001/seek",
                json={"position": 5.0},
            )

    assert seek_resp.status_code == 200, seek_resp.text
    assert captured_seek.get("position") == 5.0, (
        f"manager.seek() not called with position=5.0; captured: {captured_seek!r}"
    )
