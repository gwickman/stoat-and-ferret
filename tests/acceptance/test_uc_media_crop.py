# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_crop — crop effect changes output dimensions (BL-796 AC-3).

Generates a video-only fixture, applies a crop effect, renders, then asserts via ffprobe
that output dimensions match the crop parameters and via the render oracle that the
render completed successfully.

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_crop.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import CROP_EFFECT
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job
from tests.render_oracle import assert_crop_region, assert_stream_inventory

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-crop-001"

# Crop parameters: 640x360 region starting at (100, 50) from a 1280x720 source
_CROP_W = 640
_CROP_H = 360
_CROP_X = 100
_CROP_Y = 50

_SOURCE_W = 1280
_SOURCE_H = 720


def _make_video_only_fixture(path: Path, duration: int = 3) -> Path:
    """Generate a video-only MP4 using testsrc2 (no audio)."""
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
        filename="fixture.mp4",
        duration_frames=90,
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


def _make_clip(cid: str, vid_id: str, effects: list | None = None) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=cid,
        project_id=_PROJECT_ID,
        source_video_id=vid_id,
        in_point=0,
        out_point=90,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        effects=effects,
    )


def _make_render_plan() -> str:
    return json.dumps(
        {
            "total_duration": 3.0,
            "settings": {
                "output_format": "mp4",
                "codec": "libx264",
                "fps": 30.0,
                "width": _SOURCE_W,
                "height": _SOURCE_H,
                "quality_preset": "standard",
            },
        }
    )


def _make_job(plan: str, output_path: str) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-crop-001",
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


def _make_video_repo(vid: Video) -> AsyncMock:
    r: AsyncMock = AsyncMock()
    r.get = AsyncMock(return_value=vid)
    return r


def _make_clip_repo(clip: Clip) -> AsyncMock:
    r: AsyncMock = AsyncMock()
    r.list_by_project = AsyncMock(return_value=[clip])
    return r


def _make_effect_registry() -> EffectRegistry:
    registry = EffectRegistry()
    registry.register("crop", CROP_EFFECT)
    return registry


def _ffprobe_dimensions(path: Path) -> tuple[int, int]:
    """Return (width, height) of the first video stream via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "v:0",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"ffprobe failed for {path}: {result.stderr[-400:]}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise AssertionError(f"No video stream found in {path}")
    return int(streams[0]["width"]), int(streams[0]["height"])


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_crop_effect_changes_output_dimensions(tmp_path: Path) -> None:
    """Single-clip render with crop effect: output dimensions match crop parameters.

    BL-796 AC-3: acceptance test verifying that a crop effect is dispatched through the
    render path, and the output file dimensions reflect the crop (via ffprobe).
    """
    fixture = _make_video_only_fixture(tmp_path / "fixture.mp4")

    vid_id = "vid-crop-001"
    vid = _make_video(vid_id, str(fixture))
    plan = _make_render_plan()

    clip_with_crop = _make_clip(
        "clip-crop",
        vid_id,
        effects=[
            {
                "effect_type": "crop",
                "parameters": {
                    "width": _CROP_W,
                    "height": _CROP_H,
                    "x": _CROP_X,
                    "y": _CROP_Y,
                },
            }
        ],
    )
    out_path = tmp_path / "out_crop.mp4"
    job = _make_job(plan, str(out_path))

    cmd = await build_command_for_job(
        job,
        _make_clip_repo(clip_with_crop),
        _make_video_repo(vid),
        effect_registry=_make_effect_registry(),
    )

    # Assert the crop filter is in the filter_complex
    assert "-filter_complex" in cmd, "Expected -filter_complex in command with crop effect"
    fc_idx = cmd.index("-filter_complex")
    filter_complex_val = cmd[fc_idx + 1]
    expected_filter = f"crop={_CROP_W}:{_CROP_H}:{_CROP_X}:{_CROP_Y}"
    assert expected_filter in filter_complex_val, (
        f"Expected '{expected_filter}' in filter_complex: {filter_complex_val!r}"
    )

    r = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=120)
    assert r.returncode == 0, f"ffmpeg (crop effect) failed: {r.stderr.decode()[-800:]}"

    await assert_stream_inventory(out_path, video=True, audio=False)

    out_w, out_h = _ffprobe_dimensions(out_path)
    assert out_w == _CROP_W, f"Expected output width={_CROP_W}, got {out_w}"
    assert out_h == _CROP_H, f"Expected output height={_CROP_H}, got {out_h}"

    assert_crop_region(out_path, _CROP_X, _CROP_Y, _CROP_W, _CROP_H, fixture, t_frame=1.0)
