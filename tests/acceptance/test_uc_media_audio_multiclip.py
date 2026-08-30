# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance tests: multi-clip audio edge cases (BL-815).

3-clip test: distinct frequencies (A=250Hz, B=1000Hz, C=4000Hz) — asserts per-window
band presence/absence and total duration within 150ms tolerance.

Sandwich test: audio-silent-audio layout (A=440Hz audio, B=video-only, C=250Hz audio) —
exercises the anullsrc silence synthesis path in worker.py.

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
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
    assert_audio_band_window,
    assert_av_duration_alignment,
    assert_stream_inventory,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID_3CLIP = "proj-audio-3clip-001"
_PROJECT_ID_SANDWICH = "proj-audio-sandwich-001"


def _make_audio_video_fixture(path: Path, duration: int = 5, freq_hz: int = 440) -> Path:
    """Generate an audio+video MP4 with a single-frequency stereo track (amerge pattern)."""
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


def _make_video_only_fixture(path: Path, duration: int = 5) -> Path:
    """Generate a video-only MP4 (no audio stream) for the sandwich test."""
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
        raise RuntimeError(
            f"ffmpeg video-only fixture generation failed: {result.stderr.decode()[-800:]}"
        )
    return path


def _make_video(vid_id: str, path: str, audio_codec: str | None = "aac") -> Video:
    """Create a Video model pointing to a fixture file."""
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
        audio_codec=audio_codec,
    )


def _make_clip(clip_id: str, vid_id: str, project_id: str) -> Clip:
    """Create a Clip spanning the full 5-second fixture duration (0–150 frames @ 30fps)."""
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=project_id,
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


def _make_render_job(project_id: str, output_path: str, total_duration: float) -> RenderJob:
    """Create a RenderJob with the given total_duration."""
    now = datetime.now(timezone.utc)
    plan = json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "output_format": "mp4",
                "width": 320,
                "height": 240,
                "codec": "libx264",
                "quality_preset": "standard",
                "fps": 30.0,
            },
        }
    )
    return RenderJob(
        id=f"job-{project_id}",
        project_id=project_id,
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
    """Build an async mock clip repository returning the given clips."""
    repo: AsyncMock = AsyncMock()
    repo.list_by_project = AsyncMock(return_value=list(clips))
    return repo


def _make_video_repo(*videos: Video) -> AsyncMock:
    """Build an async mock video repository indexed by video ID."""
    vid_map = {v.id: v for v in videos}
    repo: AsyncMock = AsyncMock()

    async def _get(vid_id: str) -> Video | None:
        return vid_map.get(vid_id)

    repo.get = AsyncMock(side_effect=_get)
    return repo


def _probe_duration(path: Path) -> float:
    """Return file duration in seconds via ffprobe format.duration."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {r.stderr[-400:]}")
    return float(json.loads(r.stdout)["format"]["duration"])


@_FFMPEG_SKIP
async def test_uc_media_audio_3clip(tmp_path: Path) -> None:
    """3-clip render with distinct frequencies asserts per-window bands + duration (BL-815-AC-4).

    Clips: A=250Hz, B=1000Hz, C=4000Hz, each 5s with 1s acrossfade between pairs.
    Total = 5+5+5-1-1 = 13.0s.
    Output windows (acrossfade occupies 4-5s and 8-9s):
      A pure zone: 0.5–3.5s; B pure zone: 5.5–7.5s; C pure zone: 9.5–12.5s.
    B-band must be present in B window and absent in A and C windows.
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5, freq_hz=250)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5, freq_hz=1000)
    clip_c_path = _make_audio_video_fixture(tmp_path / "clip_c.mp4", duration=5, freq_hz=4000)
    out_path = tmp_path / "output.mp4"

    vid_a = _make_video("vid-a", str(clip_a_path))
    vid_b = _make_video("vid-b", str(clip_b_path))
    vid_c = _make_video("vid-c", str(clip_c_path))
    clip_a = _make_clip("clip-a", "vid-a", _PROJECT_ID_3CLIP)
    clip_b = _make_clip("clip-b", "vid-b", _PROJECT_ID_3CLIP)
    clip_c = _make_clip("clip-c", "vid-c", _PROJECT_ID_3CLIP)

    # 5+5+5 - 1 acrossfade - 1 acrossfade = 13.0s
    job = _make_render_job(_PROJECT_ID_3CLIP, str(out_path), total_duration=13.0)
    clip_repo = _make_clip_repo(clip_a, clip_b, clip_c)
    video_repo = _make_video_repo(vid_a, vid_b, vid_c)

    cmd = await build_command_for_job(job, clip_repo, video_repo)

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    await assert_stream_inventory(out_path, video=True, audio=True)

    # Per-window band assertions — B-band (1000Hz) present in B window, absent in A and C
    await assert_audio_band_window(
        out_path, 0.5, 3.5, expected_bands_hz=[250], absent_bands_hz=[1000]
    )
    await assert_audio_band_window(
        out_path, 5.5, 7.5, expected_bands_hz=[1000], absent_bands_hz=[250, 4000]
    )
    await assert_audio_band_window(
        out_path, 9.5, 12.5, expected_bands_hz=[4000], absent_bands_hz=[1000]
    )

    # Total duration within 150ms of 13.0s
    actual_dur = _probe_duration(out_path)
    assert abs(actual_dur - 13.0) <= 0.15, (
        f"Total duration {actual_dur:.3f}s deviates from 13.0s by more than 150ms"
    )


@_FFMPEG_SKIP
async def test_uc_media_audio_sandwich(tmp_path: Path) -> None:
    """Sandwich test: audio-silent-audio exercises anullsrc synthesis path (BL-815-AC-5).

    Clips: A=440Hz audio, B=video-only (anullsrc silence), C=250Hz audio, each 5s.
    Total = 13.0s with 1s acrossfades.
    Asserts: A-band in A window; silence (neither A- nor C-band) in B window;
    C-band in C window; audio stream present (anullsrc maintains audio continuity).
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5, freq_hz=440)
    clip_b_path = _make_video_only_fixture(tmp_path / "clip_b.mp4", duration=5)
    clip_c_path = _make_audio_video_fixture(tmp_path / "clip_c.mp4", duration=5, freq_hz=250)
    out_path = tmp_path / "output.mp4"

    vid_a = _make_video("vid-a", str(clip_a_path), audio_codec="aac")
    vid_b = _make_video("vid-b", str(clip_b_path), audio_codec=None)  # video-only → anullsrc
    vid_c = _make_video("vid-c", str(clip_c_path), audio_codec="aac")
    clip_a = _make_clip("clip-a", "vid-a", _PROJECT_ID_SANDWICH)
    clip_b = _make_clip("clip-b", "vid-b", _PROJECT_ID_SANDWICH)
    clip_c = _make_clip("clip-c", "vid-c", _PROJECT_ID_SANDWICH)

    job = _make_render_job(_PROJECT_ID_SANDWICH, str(out_path), total_duration=13.0)
    clip_repo = _make_clip_repo(clip_a, clip_b, clip_c)
    video_repo = _make_video_repo(vid_a, vid_b, vid_c)

    cmd = await build_command_for_job(job, clip_repo, video_repo)

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    # Audio stream must be present (anullsrc synthesis keeps audio alive through video-only clip)
    await assert_stream_inventory(out_path, video=True, audio=True)

    # Clip A window (440Hz): 0.5–3.5s
    await assert_audio_band_window(out_path, 0.5, 3.5, expected_bands_hz=[440], absent_bands_hz=[])
    # Clip B window (silence via anullsrc): 5.5–7.5s — neither A- nor C-band present
    await assert_audio_band_window(
        out_path, 5.5, 7.5, expected_bands_hz=[], absent_bands_hz=[440, 250]
    )
    # Clip C window (250Hz): 9.5–12.5s
    await assert_audio_band_window(out_path, 9.5, 12.5, expected_bands_hz=[250], absent_bands_hz=[])

    await assert_av_duration_alignment(out_path, max_delta_ms=150.0)
