# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance: demux trim (-t on zero-in-point inputs) and TTS amix=duration=shortest (BL-875).

Test 1 (FR-002-AC-1, FR-004-AC-1): multi-clip render where source files are longer than the
clip placement window (8s sources, 3s clip windows). Verifies A/V duration alignment within
150ms — confirming audio does not bleed past the clip window.

Test 2 (FR-005-AC-1): multi-clip + TTS audio longer than the project video timeline. Verifies
A/V alignment within 150ms — confirming amix=duration=shortest caps audio at the video end.

All tests are gated on STOAT_TEST_FFMPEG=1.
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_demux_trim.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import TtsCueAudioInput, build_command_for_job
from tests.render_oracle import assert_av_duration_alignment, assert_stream_inventory

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-demux-trim-001"


def _make_audio_video_fixture(path: Path, duration: int = 8, freq_hz: int = 440) -> Path:
    """Generate an audio+video MP4; amerge of two sine sources for guaranteed-stereo audio."""
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
            f"sine=frequency={freq_hz}:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq_hz}:duration={duration}",
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


def _make_tts_wav_fixture(path: Path, duration: float, freq_hz: int = 2000) -> Path:
    """Generate a synthetic TTS WAV file using a sine wave at a distinct frequency."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq_hz}:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq_hz}:duration={duration}",
            "-filter_complex",
            "amerge=inputs=2",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg TTS WAV generation failed: {result.stderr.decode()[-800:]}")
    return path


def _make_video(
    vid_id: str,
    path: str,
    duration_frames: int,
    audio_codec: str | None = "aac",
) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=vid_id,
        path=path,
        filename="fixture.mp4",
        duration_frames=duration_frames,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=320,
        height=240,
        video_codec="h264",
        file_size=500_000,
        created_at=now,
        updated_at=now,
        audio_codec=audio_codec,
    )


def _make_clip(
    clip_id: str,
    vid_id: str,
    in_point: int = 0,
    out_point: int = 90,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=vid_id,
        in_point=in_point,
        out_point=out_point,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type="file",
        effects=effects,
        source_asset_id=None,
        generator_params=None,
    )


def _make_render_job(output_path: str, total_duration: float) -> RenderJob:
    now = datetime.now(timezone.utc)
    plan = json.dumps(
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
    return RenderJob(
        id=f"job-{_PROJECT_ID}",
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
async def test_short_placement_from_long_source_audio_duration(tmp_path: Path) -> None:
    """Audio does not bleed past clip window when source is longer than placement (BL-875-AC-2,4).

    Source fixtures are 8s each; clips place only 3s (in_point=0, out_point=90 at 30fps).
    With 1s acrossfade, total timeline = 3+3-1 = 5s. The -t trim on zero-in-point inputs
    confines demuxer output to the 3s window; audio and video must align within 150ms.
    """
    src_a = _make_audio_video_fixture(tmp_path / "src_a.mp4", duration=8, freq_hz=440)
    src_b = _make_audio_video_fixture(tmp_path / "src_b.mp4", duration=8, freq_hz=880)
    out_path = tmp_path / "output.mp4"

    # 8s source, 30fps -> 240 frames; clip window = frames 0..90 -> 3s
    vid_a = _make_video("vid-dt-a", str(src_a), duration_frames=240)
    vid_b = _make_video("vid-dt-b", str(src_b), duration_frames=240)
    clip_a = _make_clip("clip-dt-a", "vid-dt-a", in_point=0, out_point=90)
    clip_b = _make_clip("clip-dt-b", "vid-dt-b", in_point=0, out_point=90)

    # total_duration = 3+3-1 = 5s (1s acrossfade)
    job = _make_render_job(str(out_path), total_duration=5.0)

    cmd = await build_command_for_job(
        job,
        _make_clip_repo(clip_a, clip_b),
        _make_video_repo(vid_a, vid_b),
    )

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    await assert_stream_inventory(out_path, video=True, audio=True)
    await assert_av_duration_alignment(out_path, max_delta_ms=150.0)


@_FFMPEG_SKIP
async def test_tts_audio_capped_at_video_duration(tmp_path: Path) -> None:
    """TTS audio does not extend beyond video stream end (BL-875-AC-5).

    Source fixtures are 3s each (in_point=0, out_point=90). TTS WAV is 20s — far longer than
    the 5s video timeline (3+3-1=5s with 1s acrossfade). amix=duration=shortest caps the
    mixed audio at the shorter input (source audio ~5s), preventing the 20s TTS from outlasting
    the video. Audio and video must align within 150ms.
    """
    src_a = _make_audio_video_fixture(tmp_path / "src_a.mp4", duration=3, freq_hz=440)
    src_b = _make_audio_video_fixture(tmp_path / "src_b.mp4", duration=3, freq_hz=880)
    # TTS WAV is 20s — much longer than the 5s video timeline
    tts_path = _make_tts_wav_fixture(tmp_path / "tts.wav", duration=20.0, freq_hz=2000)
    out_path = tmp_path / "output.mp4"

    # 3s sources, 30fps -> 90 frames; clip window = frames 0..90 -> 3s
    vid_a = _make_video("vid-tts-a", str(src_a), duration_frames=90)
    vid_b = _make_video("vid-tts-b", str(src_b), duration_frames=90)
    clip_a = _make_clip("clip-tts-a", "vid-tts-a", in_point=0, out_point=90)
    clip_b = _make_clip("clip-tts-b", "vid-tts-b", in_point=0, out_point=90)

    job = _make_render_job(str(out_path), total_duration=5.0)
    tts_inputs = [
        TtsCueAudioInput(
            cue_id="cue-tts-long",
            audio_path=str(tts_path),
            track_id="track-1",
            start_s=0.0,
            weight=1.0,
            volume_envelope=None,
        )
    ]

    cmd = await build_command_for_job(
        job,
        _make_clip_repo(clip_a, clip_b),
        _make_video_repo(vid_a, vid_b),
        tts_inputs=tts_inputs,
    )

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    await assert_stream_inventory(out_path, video=True, audio=True)
    await assert_av_duration_alignment(out_path, max_delta_ms=150.0)
