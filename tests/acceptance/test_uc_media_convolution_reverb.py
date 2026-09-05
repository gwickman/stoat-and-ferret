# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_convolution_reverb — single-clip render with convolution_reverb.

BL-827: Generates an audio+video fixture, builds the FFmpeg command via build_command_for_job
with a CONVOLUTION_REVERB effect (ir_name="hall_small", mix=0.4), executes it, then asserts:
both video and audio streams are present in the output and FFmpeg exits 0.

The IR WAV must be wired as a second -i input with a two-pad [0:a][1:a]afir= filter; without it
FFmpeg crashes at runtime. This test confirms end-to-end wiring is correct.

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_convolution_reverb.py -v
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
from stoat_ferret.effects.definitions import CONVOLUTION_REVERB
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job
from tests.render_oracle import assert_stream_inventory

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-convolution-reverb-001"


def _make_audio_video_fixture(path: Path, duration: int = 3) -> Path:
    """Generate an audio+video MP4 using the amerge stereo pattern from AGENTS.md."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x240:rate=30:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=880:duration={duration}",
            "-filter_complex",
            "amerge=inputs=2",
            "-ac",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
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
        width=320,
        height=240,
        video_codec="h264",
        file_size=100_000,
        created_at=now,
        updated_at=now,
        audio_codec="aac",
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


def _make_render_plan(total_duration: float = 3.0) -> str:
    return json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "output_format": "mp4",
                "codec": "libx264",
                "fps": 30.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
            },
        }
    )


def _make_job(plan: str, output_path: str) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-convolution-reverb",
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
    registry.register("convolution_reverb", CONVOLUTION_REVERB)
    return registry


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_convolution_reverb_render_single_clip(tmp_path: Path) -> None:
    """Single-clip render with convolution_reverb IR wiring succeeds end-to-end (BL-827 AC-1/4).

    Verifies:
    - FFmpeg command includes the IR WAV as a second -i input (stream 1)
    - filter_complex contains a two-pad [0:a][1:a]afir= segment
    - FFmpeg exits 0 (no runtime crash)
    - Output has both video and audio streams
    """
    fixture = _make_audio_video_fixture(tmp_path / "fixture.mp4")
    vid_id = "vid-reverb-eff"
    vid = _make_video(vid_id, str(fixture))
    plan = _make_render_plan()

    clip = _make_clip(
        "clip-reverb-eff",
        vid_id,
        effects=[
            {
                "effect_type": "convolution_reverb",
                "parameters": {"ir_name": "hall_small", "mix": 0.4},
            }
        ],
    )
    out_path = tmp_path / "out_reverb.mp4"
    job = _make_job(plan, str(out_path))

    cmd = await build_command_for_job(
        job,
        _make_clip_repo(clip),
        _make_video_repo(vid),
        effect_registry=_make_effect_registry(),
    )

    # Verify IR WAV appears in the -i list (stream index 1)
    assert "-i" in cmd
    i_indices = [i for i, v in enumerate(cmd) if v == "-i"]
    assert len(i_indices) >= 2, "Expected at least 2 -i inputs (clip + IR WAV)"
    ir_input = cmd[i_indices[1] + 1]
    assert ir_input.endswith("hall_small.wav"), f"Expected IR WAV at stream 1, got: {ir_input!r}"

    # Verify two-pad afir filter in filter_complex
    fc_idx = cmd.index("-filter_complex") if "-filter_complex" in cmd else -1
    assert fc_idx != -1, "Expected -filter_complex in command with convolution_reverb effect"
    filter_complex_val = cmd[fc_idx + 1]
    assert "[0:a][1:a]afir=" in filter_complex_val, (
        f"Expected two-pad [0:a][1:a]afir= in filter_complex: {filter_complex_val!r}"
    )
    assert "-an" not in cmd, "Expected no -an when audio effect is present"

    # Execute FFmpeg
    r = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=120)
    assert r.returncode == 0, f"ffmpeg (convolution_reverb) failed: {r.stderr.decode()[-800:]}"

    # Output must have both video and audio
    await assert_stream_inventory(out_path, video=True, audio=True)
