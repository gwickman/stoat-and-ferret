# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Real-render concurrent isolation proof for BL-686.

Proves that two concurrent renders targeting distinct output paths do not
cross-contaminate each other's output files.  Uses build_command_for_job
directly with mocked repos and synthetic lavfi source videos — no HTTP layer.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)

_PROJECT_ID = "proj-concurrent-001"
_NOW = datetime.now(timezone.utc)


def _make_render_plan(duration: float = 3.0) -> str:
    return json.dumps(
        {
            "total_duration": duration,
            "settings": {
                "codec": "libx264",
                "fps": 30.0,
                "width": 640,
                "height": 480,
                "quality_preset": "standard",
            },
        }
    )


def _make_job(job_id: str, output_path: str, duration: float = 3.0) -> RenderJob:
    return RenderJob(
        id=job_id,
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=output_path,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_render_plan(duration),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )


def _make_clip(clip_id: str, video_id: str, out_point: int = 90) -> Clip:
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=0,
        out_point=out_point,  # 3s at 30fps
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        effects=None,
    )


def _make_video(video_id: str, path: str) -> Video:
    return Video(
        id=video_id,
        path=path,
        filename=f"{video_id}.mp4",
        duration_frames=90,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=640,
        height=480,
        video_codec="h264",
        audio_codec=None,
        file_size=100_000,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_repos(clip: Clip, video: Video) -> tuple[AsyncMock, AsyncMock]:
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=video)
    return clip_repo, video_repo


def _gen_solid_video(path: Path, color: str, duration: float = 3.0) -> None:
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=640x480:r=30:d={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"lavfi gen failed: {r.stderr.decode()[-500:]}")


def _sha256_frame(video: Path, timestamp: str = "00:00:01") -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        frame_path = f.name
    try:
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                timestamp,
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-f",
                "image2",
                frame_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if r.returncode != 0:
            raise RuntimeError(f"Frame extract failed: {r.stderr.decode()[-300:]}")
        with open(frame_path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(frame_path)


async def _run_render_async(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    return await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=60)


def _ffprobe_duration(video_path: Path) -> float:
    """Return duration in seconds reported by ffprobe, or raise on failure."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {video_path}: {result.stderr}")
    return float(result.stdout.strip())


# ---------------------------------------------------------------------------
# BL-686: concurrent real-mode renders produce distinct, non-contaminated outputs
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_concurrent_render_distinct_outputs(tmp_path: Path) -> None:
    """BL-686: two concurrent renders produce distinct, non-cross-contaminated outputs.

    Proof:
    - Two synthetic solid-colour sources (blue, red) rendered concurrently via
      asyncio.gather.  Both submitted before either is polled.
    - Asserts: distinct output paths, files exist, non-zero size, sha256 frame
      hashes differ (content-distinct, not just name-distinct).

    Discharge command (STOAT_TEST_FFMPEG=1):
        uv run pytest tests/test_render/test_worker_render.py \
            ::test_concurrent_render_distinct_outputs -v
    """
    # Generate two visually-distinct source videos
    src_blue = tmp_path / "blue_source.mp4"
    src_red = tmp_path / "red_source.mp4"
    _gen_solid_video(src_blue, color="blue", duration=3.0)
    _gen_solid_video(src_red, color="red", duration=3.0)

    out1 = tmp_path / "render_job1.mp4"
    out2 = tmp_path / "render_job2.mp4"

    job1 = _make_job("job-concurrent-001", str(out1))
    job2 = _make_job("job-concurrent-002", str(out2))

    clip1 = _make_clip("clip-concurrent-001", "vid-concurrent-001")
    clip2 = _make_clip("clip-concurrent-002", "vid-concurrent-002")

    video1 = _make_video("vid-concurrent-001", str(src_blue))
    video2 = _make_video("vid-concurrent-002", str(src_red))

    clip_repo1, video_repo1 = _make_repos(clip1, video1)
    clip_repo2, video_repo2 = _make_repos(clip2, video2)

    # Build both commands before running either (genuine concurrent submission)
    cmd1, cmd2 = await asyncio.gather(
        build_command_for_job(job1, clip_repo1, video_repo1),
        build_command_for_job(job2, clip_repo2, video_repo2),
    )

    # Run both renders concurrently — neither waits for the other to start
    r1, r2 = await asyncio.gather(
        _run_render_async(cmd1),
        _run_render_async(cmd2),
    )

    # FR-001-AC-1: both renders complete without error
    assert r1.returncode == 0, f"Render 1 (blue) failed:\n{r1.stderr.decode()[-800:]}"
    assert r2.returncode == 0, f"Render 2 (red) failed:\n{r2.stderr.decode()[-800:]}"

    # Distinct output paths
    assert str(out1) != str(out2), "Output paths must be distinct"

    # Output files exist and are non-zero (BL-686-AC-2 file-existence check)
    assert out1.exists() and out1.stat().st_size > 0, "Output 1 missing or empty"
    assert out2.exists() and out2.stat().st_size > 0, "Output 2 missing or empty"

    # FR-002-AC-1: frame hashes differ — content-distinct, no cross-contamination
    hash1 = _sha256_frame(out1, timestamp="00:00:01")
    hash2 = _sha256_frame(out2, timestamp="00:00:01")
    assert hash1 != hash2, (
        "Frame hashes are identical — outputs may be cross-contaminated "
        f"(hash1={hash1[:12]}…, hash2={hash2[:12]}…)"
    )

    # BL-686-AC-2: verify each output is a valid video with non-zero duration
    for output_path in [out1, out2]:
        duration = _ffprobe_duration(output_path)
        assert duration > 0, f"Expected non-zero duration for {output_path}"
