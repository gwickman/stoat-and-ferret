# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_multiclip_assemble — multi-clip render with source audio (BL-791 AC-3).

Generates two 5-second audio+video fixtures via the amerge stereo pattern, builds
the FFmpeg command via build_command_for_job, executes it, then asserts the oracle:
audio stream present and A/V duration within 100ms.

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_multiclip_assemble.py -v
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
    assert_av_duration_alignment,
    assert_stream_inventory,
    assert_transition_reference,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-multiclip-audio-001"


def _make_audio_video_fixture(path: Path, duration: int = 5) -> Path:
    """Generate an audio+video MP4 using the amerge stereo pattern from AGENTS.md.

    Uses two independent sine sources (440Hz, 880Hz) merged to stereo with amerge=inputs=2.
    This guarantees 2-channel output on all FFmpeg builds (unlike aevalsrc:c=stereo).
    """
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
    """Create a Video model pointing to an actual audio+video fixture file."""
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
        audio_codec="aac",
    )


def _make_clip(clip_id: str, vid_id: str) -> Clip:
    """Create a Clip spanning the full 5-second fixture duration (0–150 frames @ 30fps)."""
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


def _make_job(output_path: str) -> RenderJob:
    """Create a RenderJob for a two-clip, 1s-acrossfade multi-clip render.

    total_duration = clip_a_duration + clip_b_duration - acrossfade_duration
                   = 5 + 5 - 1 = 9.0s
    """
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
                "fps": 30.0,
            },
        }
    )
    return RenderJob(
        id="job-multiclip-audio-001",
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


@_FFMPEG_SKIP
async def test_uc_media_multiclip_assemble_audio(tmp_path: Path) -> None:
    """Multi-clip render produces sequenced source audio: stream present, A/V aligned (BL-791 AC-3).

    Steps:
    1. Generate two 5s audio+video fixtures via amerge stereo pattern.
    2. Build the FFmpeg command via build_command_for_job (multi-clip path activated
       by two clips -> acrossfade chain in filter_complex).
    3. Execute the command.
    4. Oracle asserts: audio stream present + A/V duration within 100ms.
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5)
    out_path = tmp_path / "output.mp4"

    vid_a = _make_video("vid-a", str(clip_a_path))
    vid_b = _make_video("vid-b", str(clip_b_path))
    clip_a = _make_clip("clip-a", "vid-a")
    clip_b = _make_clip("clip-b", "vid-b")

    job = _make_job(str(out_path))
    clip_repo = _make_clip_repo(clip_a, clip_b)
    video_repo = _make_video_repo(vid_a, vid_b)

    cmd = await build_command_for_job(job, clip_repo, video_repo)

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists(), "Output file must exist after render"
    assert out_path.stat().st_size > 0, "Output file must be non-empty"

    await assert_stream_inventory(out_path, video=True, audio=True)
    await assert_av_duration_alignment(out_path, max_delta_ms=100.0)


def _render_xfade_ref(
    clip_a: Path,
    clip_b: Path,
    out: Path,
    transition: str,
    duration: float,
    offset: float,
) -> None:
    """Render two clips joined by an xfade transition into *out* for oracle reference."""
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-i",
            str(clip_a),
            "-i",
            str(clip_b),
            "-filter_complex",
            (
                f"[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                f"[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                f"[pv0][pn1]xfade=transition={transition}:duration={duration}"
                f":offset={offset}[xf0];[xf0]format=yuv420p[final]"
            ),
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(out),
        ],
        capture_output=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f"xfade ref render failed: {r.stderr.decode()[-800:]}")


_PROJECT_ID_TR = "proj-multiclip-transition-001"


def _make_job_with_transition(
    output_path: str,
    clip_a_id: str,
    transition_type: str,
    duration: float,
    total_duration: float,
) -> RenderJob:
    """Create a RenderJob with a saved transition in the render_plan settings."""
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
                "transitions": [
                    {
                        "clip_a_id": clip_a_id,
                        "transition_type": transition_type,
                        "duration": duration,
                    }
                ],
            },
        }
    )
    return RenderJob(
        id="job-multiclip-transition-001",
        project_id=_PROJECT_ID_TR,
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


def _make_clip_tr(clip_id: str, vid_id: str) -> Clip:
    """Create a Clip for the transition test (5s at 30fps, in_point=0)."""
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID_TR,
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


@_FFMPEG_SKIP
async def test_uc_media_multiclip_assemble_wipeleft_transition(tmp_path: Path) -> None:
    """Saved wipeleft/0.35 transition renders at seam and audio is aligned (BL-792 AC-3).

    Steps:
    1. Generate two 5s audio+video fixtures.
    2. Build the FFmpeg command via build_command_for_job with wipeleft/0.35 in transitions.
    3. Execute the command.
    4. Build a reference render with the same wipeleft/0.35 xfade for oracle comparison.
    5. Oracle asserts: visual seam matches saved transition + A/V duration aligned.
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5)
    out_path = tmp_path / "output.mp4"
    ref_path = tmp_path / "ref.mp4"

    clip_a_id = "clip-a-tr"
    clip_b_id = "clip-b-tr"
    vid_a = _make_video("vid-a-tr", str(clip_a_path))
    vid_b = _make_video("vid-b-tr", str(clip_b_path))
    clip_a = _make_clip_tr(clip_a_id, "vid-a-tr")
    clip_b = _make_clip_tr(clip_b_id, "vid-b-tr")

    # clip A = 5s, clip B = 5s, wipeleft/0.35 => total = 9.65s, offset = 4.65
    job = _make_job_with_transition(str(out_path), clip_a_id, "wipeleft", 0.35, 9.65)
    clip_repo = _make_clip_repo(clip_a, clip_b)
    video_repo = _make_video_repo(vid_a, vid_b)

    cmd = await build_command_for_job(job, clip_repo, video_repo)

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists(), "Output file must exist after render"
    assert out_path.stat().st_size > 0, "Output file must be non-empty"

    # Build reference: same clips, same wipeleft/0.35 xfade at offset=4.65
    seam_t = 4.65  # = 5.0 - 0.35 (transition starts when clip A's remainder ends)
    _render_xfade_ref(clip_a_path, clip_b_path, ref_path, "wipeleft", 0.35, seam_t)

    # Visual seam: transition style must match saved wipeleft/0.35
    assert_transition_reference(out_path, seam_t, "wipeleft", 0.35, ref_path)

    # Audio acrossfade: A/V duration must be aligned (outgoing_transition fixes acrossfade)
    await assert_av_duration_alignment(out_path, max_delta_ms=100.0)
