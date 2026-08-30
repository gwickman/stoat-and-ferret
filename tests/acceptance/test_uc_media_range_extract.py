# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UC-MEDIA-RANGE-EXTRACT acceptance test (BL-790).

Verifies that a single-clip render with a non-zero in_point produces output
frames from the correct source range. Uses a time-varying testsrc2 lavfi
fixture so SSIM comparison is meaningful (solid-color fixtures would trivially
match any offset).
"""

from __future__ import annotations

import dataclasses
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
    assert_frame_rate,
    assert_inpoint_identity,
    assert_seam_frame_order,
    assert_stream_inventory,
)

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)

_PROJECT_ID = "proj-range-extract-001"
_PROJECT_ID_MC = "proj-range-extract-mc-001"


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
    assert_inpoint_identity(
        out,
        output_t=3.0,
        source=src,
        source_start=3.0,
        source_end=9.0,
        check_start=True,
        check_end=True,
    )
    await assert_stream_inventory(out, video=True, audio=False)
    await assert_frame_count(out, expected_frames=180, tolerance=2)


@_FFMPEG_SKIP
async def test_uc_media_range_extract_mismatched_fps(tmp_path: Path) -> None:
    """24fps source with 30fps render uses source fps for in_point seek (BL-811).

    Source: testsrc2=size=320x240:rate=24:duration=10 (time-varying, 240 frames).
    Clip: in_point=48 (2.0s at 24fps), out_point=144 (6.0s at 24fps) -> 4.0s output.
    Render plan: fps=30.0 (output cadence differs from source fps).
    Oracle: SSIM identity at output midpoint vs source midpoint; threshold >= 0.95.
    """
    src = tmp_path / "src_testsrc2_24fps.mp4"
    out = tmp_path / "output_mismatched_fps.mp4"

    _gen_lavfi_video(src, "testsrc2=size=320x240:rate=24:duration=10")

    # 24fps source: 240 frames over 10s
    video = dataclasses.replace(
        _make_video("vid-mm-001", str(src)),
        frame_rate_numerator=24,
        frame_rate_denominator=1,
        duration_frames=240,
    )
    clip = _make_clip("clip-mm-001", "vid-mm-001", in_point=48, out_point=144)

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=video)

    # total_duration = (out_point - in_point) / source_fps = (144 - 48) / 24 = 4.0s
    job = _make_job(str(out), total_duration=4.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed (exit {r.returncode}):\n{r.stderr.decode()[-800:]}"
    assert out.exists(), "Output file must exist"
    assert out.stat().st_size > 0, "Output file must be non-empty"

    # output_t=2.0s is the midpoint of the 4s output (= source midpoint at (2.0+6.0)/2 = 4.0s)
    assert_inpoint_identity(
        out, output_t=2.0, source=src, source_start=2.0, source_end=6.0, threshold=0.95
    )
    await assert_stream_inventory(out, video=True, audio=False)


def _make_mc_job(output_path: str, total_duration: float) -> RenderJob:
    """RenderJob for multi-clip range-extract test (project=_PROJECT_ID_MC)."""
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
        id="job-mc-range-001",
        project_id=_PROJECT_ID_MC,
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
async def test_uc_media_multiclip_range_extract(tmp_path: Path) -> None:
    """Two-clip render where clip_b has non-zero in_point; asserts correct source range (BL-813).

    Source: testsrc2=size=320x240:rate=30:duration=10 (time-varying, 300 frames).
    clip_a: in_point=0, out_point=60 → 2.0s output (source 0–2s).
    clip_b: in_point=90 (3.0s), out_point=150 (5.0s) → 2.0s output (source 3–5s).
    Total output: 4.0s. Seam at t=2.0s.
    Oracle: assert_frame_count (120 frames); assert_inpoint_identity at clip_b midpoint
    (source_start=3.0, source_end=5.0, output_t=3.0, threshold=0.9);
    assert_seam_frame_order at seam_t=2.0 with threshold=0.5;
    assert_stream_inventory(video=True, audio=False).
    """
    src = tmp_path / "src_testsrc2.mp4"
    out = tmp_path / "output_mc.mp4"

    _gen_lavfi_video(src, "testsrc2=size=320x240:rate=30:duration=10")

    video = _make_video("vid-mc-001", str(src))
    now = datetime.now(timezone.utc)
    clip_a = Clip(
        id="clip-mc-a",
        project_id=_PROJECT_ID_MC,
        source_video_id="vid-mc-001",
        in_point=0,
        out_point=60,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type="file",
        effects=None,
        source_asset_id=None,
        generator_params=None,
    )
    clip_b = Clip(
        id="clip-mc-b",
        project_id=_PROJECT_ID_MC,
        source_video_id="vid-mc-001",
        in_point=90,
        out_point=150,
        timeline_position=60,
        created_at=now,
        updated_at=now,
        clip_type="file",
        effects=None,
        source_asset_id=None,
        generator_params=None,
    )

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip_a, clip_b])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=video)

    # total = clip_a(2.0s) + clip_b(2.0s) = 4.0s (no audio acrossfade: video-only)
    job = _make_mc_job(str(out), total_duration=4.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed (exit {r.returncode}):\n{r.stderr.decode()[-800:]}"
    assert out.exists(), "Output file must exist"
    assert out.stat().st_size > 0, "Output file must be non-empty"

    # clip_b midpoint: output_t=3.0 maps to source_t=(3.0+5.0)/2=4.0
    assert_inpoint_identity(
        out,
        output_t=3.0,
        source=src,
        source_start=3.0,
        source_end=5.0,
        threshold=0.9,
    )
    # Seam at 2.0s; use delta=0.3 to avoid the ±50ms tight window that can return 0
    # frames from filter-complex renders. pre_t/post_t match output times at seam_t±delta.
    # output[1.7] = clip_a source[1.7]; output[2.3] = clip_b source[3.0+0.3=3.3].
    assert_seam_frame_order(
        out,
        seam_t=2.0,
        pre_source=src,
        pre_t=1.7,
        post_source=src,
        post_t=3.3,
        threshold=0.5,
        delta=0.3,
    )
    await assert_stream_inventory(out, video=True, audio=False)
    await assert_frame_count(out, expected_frames=120, tolerance=2)


@_FFMPEG_SKIP
async def test_uc_media_range_extract_24fps_60fps_output(tmp_path: Path) -> None:
    """24fps source with non-zero in_point rendered at 60fps (BL-813 FR-007).

    Source: testsrc2=size=320x240:rate=24:duration=10 (time-varying, 240 frames).
    Clip: in_point=48 (2.0s at 24fps), out_point=144 (6.0s at 24fps) → 4.0s output.
    Render plan: fps=60.0 — output cadence differs from source fps.
    Oracle: assert_inpoint_identity at midpoint; assert_frame_rate(60, 1).
    """
    src = tmp_path / "src_24fps.mp4"
    out = tmp_path / "output_60fps.mp4"

    _gen_lavfi_video(src, "testsrc2=size=320x240:rate=24:duration=10")

    video = dataclasses.replace(
        _make_video("vid-60fps-001", str(src)),
        frame_rate_numerator=24,
        frame_rate_denominator=1,
        duration_frames=240,
    )
    clip = _make_clip("clip-60fps-001", "vid-60fps-001", in_point=48, out_point=144)

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=video)

    # total_duration = (144 - 48) / 24 = 4.0s; render at 60fps
    now = datetime.now(timezone.utc)
    plan_60fps = json.dumps(
        {
            "total_duration": 4.0,
            "settings": {
                "codec": "libx264",
                "fps": 60.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
            },
        }
    )
    job = RenderJob(
        id="job-60fps-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=str(out),
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=plan_60fps,
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed (exit {r.returncode}):\n{r.stderr.decode()[-800:]}"
    assert out.exists(), "Output file must exist"
    assert out.stat().st_size > 0, "Output file must be non-empty"

    # output_t=2.0s is the midpoint of the 4s output (source midpoint at (2.0+6.0)/2=4.0s)
    assert_inpoint_identity(
        out, output_t=2.0, source=src, source_start=2.0, source_end=6.0, threshold=0.9
    )
    await assert_frame_rate(out, expected_num=60, expected_den=1)
