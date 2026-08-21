# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_audio_annotation — loudness_normalize audio chain (BL-823 AC-6).

Generates an audio+video fixture via the amerge stereo pattern, builds the FFmpeg command
via build_command_for_job with a LOUDNESS_NORMALIZE effect, executes it, then asserts the oracle:
audio RMS changed by >= 5 dB and video SSIM >= 0.99 (byte-stable).

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_audio_annotation.py -v
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
from stoat_ferret.effects.definitions import LOUDNESS_NORMALIZE
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job
from tests.render_oracle import (
    assert_audio_rms_changed,
    assert_stream_inventory,
    compute_ssim,
    measure_audio_rms_db,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-audio-annotation-001"


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
            "amerge=inputs=2,volume=0.1",
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
        id="job-audio-annotation",
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
    registry.register("loudness_normalize", LOUDNESS_NORMALIZE)
    return registry


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_loudness_normalize_routes_to_audio_chain(tmp_path: Path) -> None:
    """Single-clip render: loudness_normalize effect changes RMS by >= 5 dB; video SSIM >= 0.99.

    BL-823 AC-6: acceptance test verifying that a newly-annotated audio effect (loudness_normalize)
    is dispatched to the audio chain (not silently dropped into the video filtergraph).
    """
    fixture = _make_audio_video_fixture(tmp_path / "fixture.mp4")

    vid_id = "vid-audio-ann"
    vid = _make_video(vid_id, str(fixture))

    plan = _make_render_plan()

    # --- Render WITHOUT effect: measure baseline RMS ---
    clip_no_eff = _make_clip("clip-no-eff", vid_id, effects=None)
    out_no_eff = tmp_path / "out_no_effect.mp4"
    job_no_eff = _make_job(plan, str(out_no_eff))

    cmd_no_eff = await build_command_for_job(
        job_no_eff,
        _make_clip_repo(clip_no_eff),
        _make_video_repo(vid),
    )
    r = await asyncio.to_thread(subprocess.run, cmd_no_eff, capture_output=True, timeout=120)
    assert r.returncode == 0, f"ffmpeg (no-effect) failed: {r.stderr.decode()[-800:]}"
    await assert_stream_inventory(out_no_eff, video=True, audio=True)
    baseline_rms_db = await measure_audio_rms_db(out_no_eff)

    # --- Render WITH loudness_normalize effect: measure effect RMS ---
    clip_with_eff = _make_clip(
        "clip-with-eff",
        vid_id,
        effects=[{"effect_type": "loudness_normalize", "parameters": {}}],
    )
    out_with_eff = tmp_path / "out_with_effect.mp4"
    job_with_eff = _make_job(plan, str(out_with_eff))

    cmd_with_eff = await build_command_for_job(
        job_with_eff,
        _make_clip_repo(clip_with_eff),
        _make_video_repo(vid),
        effect_registry=_make_effect_registry(),
    )

    # Assert the audio chain is in the filter_complex (not just -an or missing)
    fc_idx = cmd_with_eff.index("-filter_complex") if "-filter_complex" in cmd_with_eff else -1
    assert fc_idx != -1, "Expected -filter_complex in command with audio effect"
    filter_complex_val = cmd_with_eff[fc_idx + 1]
    assert "[0:a]" in filter_complex_val, (
        f"Expected [0:a] audio chain in filter_complex: {filter_complex_val!r}"
    )
    assert "-an" not in cmd_with_eff, "Expected no -an when audio effect is present"

    r2 = await asyncio.to_thread(subprocess.run, cmd_with_eff, capture_output=True, timeout=120)
    assert r2.returncode == 0, f"ffmpeg (with-effect) failed: {r2.stderr.decode()[-800:]}"
    await assert_stream_inventory(out_with_eff, video=True, audio=True)
    effect_rms_db = await measure_audio_rms_db(out_with_eff)

    # Audio RMS must differ by >= 5 dB (loudnorm targeting -16 LUFS from full-scale sine ≈ -3 dBFS)
    assert_audio_rms_changed(effect_rms_db, baseline_rms_db, min_delta_db=5.0)

    # Video must be byte-stable (SSIM >= 0.99)
    ssim = compute_ssim(out_with_eff, 0.5, out_no_eff, 0.5)
    assert ssim >= 0.99, f"Video SSIM {ssim:.4f} < 0.99 after audio effect"
