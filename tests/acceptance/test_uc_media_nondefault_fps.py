# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_nondefault_fps — output_fps at configured cadence (BL-793 AC-7).

Asserts that a project configured with output_fps=24 produces an MP4 whose
r_frame_rate is 24/1, not the source-video cadence (30fps).

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_nondefault_fps.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job
from tests.render_oracle import assert_frame_rate

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-nondefault-fps-001"


def _make_video_fixture(path: Path, duration: int = 5) -> Path:
    """Generate a 30fps video-only MP4 fixture via lavfi testsrc2."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x240:rate=30:duration={duration}",
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
        filename="fixture.mp4",
        duration_frames=150,  # 5s @ 30fps
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


def _make_clip(clip_id: str, vid_id: str) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=vid_id,
        in_point=0,
        out_point=150,  # 5s @ 30fps
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type="file",
        effects=None,
        source_asset_id=None,
        generator_params=None,
    )


def _make_job(output_path: str, output_fps: float) -> RenderJob:
    now = datetime.now(timezone.utc)
    plan = json.dumps(
        {
            "total_duration": 9.0,
            "settings": {
                "output_format": "mp4",
                "width": 320,
                "height": 240,
                "codec": "libx264",
                "quality_preset": "standard",
                "fps": output_fps,
            },
        }
    )
    return RenderJob(
        id="job-nondefault-fps-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=output_path,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=plan,
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_clip_repo(*clips: Clip) -> AsyncMock:
    repo: AsyncMock = AsyncMock()
    repo.list_by_project = AsyncMock(return_value=list(clips))
    return repo


def _make_video_repo(*videos: Video) -> AsyncMock:
    vid_map = {v.id: v for v in videos}
    repo: AsyncMock = AsyncMock()

    async def _get(vid_id: str) -> Video | None:
        return vid_map.get(vid_id)

    repo.get = AsyncMock(side_effect=_get)
    return repo


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_uc_media_nondefault_fps_renders_at_24(tmp_path: Path) -> None:
    """output_fps=24 project renders at 24fps, not source cadence (30fps) (BL-793-AC-7).

    Steps:
    1. Generate two 30fps video fixtures via lavfi testsrc2.
    2. Build the FFmpeg command with fps=24.0 plan.
    3. Execute the command.
    4. Oracle asserts r_frame_rate == 24/1.
    """
    clip_a_path = _make_video_fixture(tmp_path / "clip_a.mp4", duration=5)
    clip_b_path = _make_video_fixture(tmp_path / "clip_b.mp4", duration=5)
    out_path = tmp_path / "output_24fps.mp4"

    vid_a = _make_video("vid-a", str(clip_a_path))
    vid_b = _make_video("vid-b", str(clip_b_path))
    clip_a = _make_clip("clip-a", "vid-a")
    clip_b = _make_clip("clip-b", "vid-b")

    job = _make_job(str(out_path), output_fps=24.0)
    clip_repo = _make_clip_repo(clip_a, clip_b)
    video_repo = _make_video_repo(vid_a, vid_b)

    cmd = await build_command_for_job(job, clip_repo, video_repo)

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists(), "Output file must exist after render"
    assert out_path.stat().st_size > 0, "Output file must be non-empty"

    await assert_frame_rate(out_path, expected_num=24, expected_den=1)
