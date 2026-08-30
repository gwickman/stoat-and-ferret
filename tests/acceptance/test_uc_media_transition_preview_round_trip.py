# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_transition_preview_round_trip — preview survives saved transitions.

Verifies BL-848 AC-3: POST /effects/transition → POST /preview/start → 202 (not 500 KeyError).

The effects endpoint stores {parameters: {duration, offset}} (nested shape).
Before the fix, start_preview did float(t['duration']) — KeyError on any project
with a saved transition. This test exercises the full API round-trip.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import PreviewQuality, PreviewSession, PreviewStatus, Video
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.preview.manager import PreviewManager
from tests.test_api.conftest import InMemoryAssetRepository

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

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


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_preview_start_after_transition_returns_202() -> None:
    """POST /preview/start returns 202 after a transition is saved via /effects/transition.

    Verifies BL-848: preview.py used float(t['duration']) which KeyErrors on the nested
    parameters shape that /effects/transition stores.  With the fix, 202 is returned.
    """
    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    video_a = _make_video("vid-tr-a", "/fake/clip_a.mp4")
    video_b = _make_video("vid-tr-b", "/fake/clip_b.mp4")
    await video_repo.add(video_a)
    await video_repo.add(video_b)

    now = datetime.now(timezone.utc)
    mock_manager = MagicMock(spec=PreviewManager)

    async def _return_generating_session(**kwargs: object) -> PreviewSession:
        return PreviewSession(
            id="sess-tr-001",
            project_id="",
            status=PreviewStatus.GENERATING,
            manifest_path=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )

    mock_manager.start = AsyncMock(side_effect=_return_generating_session)

    async def _return_ready_session(session_id: str) -> PreviewSession:
        return PreviewSession(
            id=session_id,
            project_id="",
            status=PreviewStatus.READY,
            manifest_path="/hls/sess-tr-001/index.m3u8",
            error_message=None,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )

    mock_manager.get_status = AsyncMock(side_effect=_return_ready_session)

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        preview_manager=mock_manager,
        asset_repository=InMemoryAssetRepository(),
    )

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": "transition-preview-test",
                "output_width": _SOURCE_W,
                "output_height": _SOURCE_H,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, proj_resp.text
        project_id = proj_resp.json()["id"]

        clip_a_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "file",
                "source_video_id": "vid-tr-a",
                "in_point": 0,
                "out_point": 60,
                "timeline_position": 0,
                "timeline_start": 0.0,
                "timeline_end": 2.0,
            },
        )
        assert clip_a_resp.status_code == 201, clip_a_resp.text
        clip_a_id = clip_a_resp.json()["id"]

        clip_b_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "file",
                "source_video_id": "vid-tr-b",
                "in_point": 0,
                "out_point": 60,
                "timeline_position": 60,
                "timeline_start": 2.0,
                "timeline_end": 4.0,
            },
        )
        assert clip_b_resp.status_code == 201, clip_b_resp.text
        clip_b_id = clip_b_resp.json()["id"]

        # POST /effects/transition — stores nested parameters shape that triggered BL-848
        tr_resp = await client.post(
            f"/api/v1/projects/{project_id}/effects/transition",
            json={
                "source_clip_id": clip_a_id,
                "target_clip_id": clip_b_id,
                "transition_type": "fade",
                "parameters": {"duration": 0.5},
            },
        )
        assert tr_resp.status_code == 201, tr_resp.text

        # POST /preview/start — was crashing with KeyError: 'duration' before the fix
        start_resp = await client.post(f"/api/v1/projects/{project_id}/preview/start")

    assert start_resp.status_code == 202, start_resp.text
    session_id = start_resp.json()["session_id"]
    assert session_id is not None

    # Poll status — mock returns READY with manifest_path set
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        status_resp = await client.get(f"/api/v1/preview/{session_id}")
    assert status_resp.status_code == 200, status_resp.text
    data = status_resp.json()
    assert data.get("manifest_url") is not None, f"manifest_url is None: {data}"
