# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_preview_parity — preview uses full composition graph (BL-797 AC-1).

Starts a preview session for a multi-clip project and asserts that:
- The session is created successfully (HTTP 202)
- The FFmpeg command receives multiple -i inputs (one per clip)

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_preview_parity.py -v
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

_PROJECT_ID = "proj-preview-parity-001"
_SOURCE_W = 640
_SOURCE_H = 360


def _make_video_fixture(path: Path, duration: int = 2) -> Path:
    """Generate a small test video using lavfi testsrc2."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={_SOURCE_W}x{_SOURCE_H}:rate=30:duration={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg fixture generation failed: {result.stderr.decode()[-800:]}")
    return path


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
async def test_preview_start_receives_multiple_inputs(tmp_path: Path) -> None:
    """Preview start for a two-clip project calls manager.start with two input paths.

    Verifies AC-1: the start handler builds a composition graph and passes
    input_paths with one entry per clip (not just clips[0]).
    """
    vid_a = tmp_path / "clip_a.mp4"
    vid_b = tmp_path / "clip_b.mp4"
    _make_video_fixture(vid_a)
    _make_video_fixture(vid_b)

    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    video_a = _make_video("vid-a", str(vid_a))
    video_b = _make_video("vid-b", str(vid_b))
    await video_repo.add(video_a)
    await video_repo.add(video_b)

    captured_input_paths: list[str] = []

    mock_manager = MagicMock(spec=PreviewManager)

    async def _capture_start(**kwargs: object) -> PreviewSession:
        from datetime import timedelta

        captured_input_paths.extend(kwargs.get("input_paths", []))  # type: ignore[arg-type]
        now = datetime.now(timezone.utc)
        return PreviewSession(
            id="sess-001",
            project_id=_PROJECT_ID,
            status=PreviewStatus.INITIALIZING,
            manifest_path=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
            quality_level=PreviewQuality.MEDIUM,
        )

    mock_manager.start = AsyncMock(side_effect=_capture_start)

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
                "name": "preview-parity-test",
                "output_width": _SOURCE_W,
                "output_height": _SOURCE_H,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, proj_resp.text
        project_id = proj_resp.json()["id"]

        # Create clips via HTTP API — BL-831 fix propagates timeline_start/timeline_end
        clip_a_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "file",
                "source_video_id": "vid-a",
                "in_point": 0,
                "out_point": 60,
                "timeline_position": 0,
                "timeline_start": 0.0,
                "timeline_end": 2.0,
            },
        )
        assert clip_a_resp.status_code == 201, clip_a_resp.text
        clip_b_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "file",
                "source_video_id": "vid-b",
                "in_point": 0,
                "out_point": 60,
                "timeline_position": 60,
                "timeline_start": 2.0,
                "timeline_end": 4.0,
            },
        )
        assert clip_b_resp.status_code == 201, clip_b_resp.text

        with patch("stoat_ferret.api.routers.preview.shutil.which", return_value="/usr/bin/ffmpeg"):
            start_resp = await client.post(f"/api/v1/projects/{project_id}/preview/start")

    assert start_resp.status_code == 202, start_resp.text
    assert len(captured_input_paths) == 2, (
        f"expected 2 input paths for 2-clip project, got {captured_input_paths!r}"
    )
