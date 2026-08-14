# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UC-MEDIA-RANGE-EXTRACT acceptance test (BL-790).

Verifies that a single-clip render with a non-zero in_point produces output
frames from the correct source range. Uses a time-varying testsrc2 lavfi
fixture so SSIM comparison is meaningful (solid-color fixtures would trivially
match any offset).
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
from tests.render_oracle import (
    assert_frame_count,
    assert_inpoint_identity,
    assert_stream_inventory,
)

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)

_PROJECT_ID = "proj-range-extract-001"


def _gen_lavfi_video(path: Path, lavfi_expr: str, timeout: int = 60) -> None:
    """Generate a test video from a lavfi source expression."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            lavfi_expr,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lavfi generation failed: {r.stderr.decode()[-800:]}")


def _make_clip(clip_id: str, video_id: str, in_point: int, out_point: int) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=in_point,
        out_point=out_point,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type="file",
        effects=None,
        source_asset_id=None,
        generator_params=None,
    )


def _make_video(video_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=video_id,
        path=path,
        filename="src.mp4",
        duration_frames=300,  # 10s @ 30fps
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=320,
        height=240,
        video_codec="h264",
        file_size=200_000,
        created_at=now,
        updated_at=now,
        audio_codec=None,
    )


def _make_job(output_path: str, total_duration: float) -> RenderJob:
    now = datetime.now(timezone.utc)
    plan = json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "codec": "libx264",
                "fps": 30.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
            },
        }
    )
    return RenderJob(
        id="job-range-extract-001",
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


@_FFMPEG_SKIP
async def test_uc_media_range_extract_nonzero_inpoint(tmp_path: Path) -> None:
    """Non-zero in_point clip renders the correct source frames (BL-790).

    Source: testsrc2=size=320x240:rate=30:duration=10 (time-varying, 300 frames).
    Clip: in_point=90 (3.0s), out_point=270 (9.0s) -> 6.0s / 180 frames of output.
    Oracle: SSIM identity at output midpoint vs source midpoint; video-only stream;
    frame count within tolerance.
    """
    src = tmp_path / "src_testsrc2.mp4"
    out = tmp_path / "output.mp4"

    _gen_lavfi_video(src, "testsrc2=size=320x240:rate=30:duration=10")

    clip = _make_clip("clip-re-001", "vid-re-001", in_point=90, out_point=270)
    video = _make_video("vid-re-001", str(src))

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=video)

    # total_duration = (out_point - in_point) / fps = (270 - 90) / 30 = 6.0s
    job = _make_job(str(out), total_duration=6.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed (exit {r.returncode}):\n{r.stderr.decode()[-800:]}"
    assert out.exists(), "Output file must exist"
    assert out.stat().st_size > 0, "Output file must be non-empty"

    # output_t=3.0s is the midpoint of the 6s output (= source midpoint at (3.0+9.0)/2 = 6.0s)
    assert_inpoint_identity(out, output_t=3.0, source=src, source_start=3.0, source_end=9.0)
    await assert_stream_inventory(out, video=True, audio=False)
    await assert_frame_count(out, expected_frames=180, tolerance=2)
