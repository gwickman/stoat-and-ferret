# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_audio_video_only — audio effect on video-only clip (BL-824 AC-4).

Creates a real video-only fixture via FFmpeg (no audio stream), then verifies that
submitting a render job with an audio effect raises CommandBuildError before FFmpeg
invocation. Gated on STOAT_TEST_FFMPEG=1 because it creates a real FFmpeg fixture.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import VOLUME
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import CommandBuildError, build_command_for_job

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID = "proj-audio-video-only-001"


def _make_video_only_fixture(path: Path, duration: int = 2) -> None:
    """Create a video-only MP4 with no audio stream using testsrc2."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x240:rate=30:duration={duration}",
            "-an",
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
        raise RuntimeError(f"FFmpeg fixture creation failed: {result.stderr.decode()}")


def _make_render_plan() -> str:
    return json.dumps(
        {
            "total_duration": 2.0,
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


def _make_video(vid_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=vid_id,
        path=path,
        filename="video_only_fixture.mp4",
        duration_frames=60,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=320,
        height=240,
        video_codec="h264",
        file_size=50_000,
        created_at=now,
        updated_at=now,
        audio_codec=None,  # video-only: no audio stream
    )


def _make_clip(cid: str, vid_id: str, effects: list | None = None) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=cid,
        project_id=_PROJECT_ID,
        source_video_id=vid_id,
        in_point=0,
        out_point=60,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        effects=effects,
    )


def _make_job(output_path: str) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-audio-video-only-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=output_path,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_render_plan(),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_audio_effect_on_video_only_raises_command_build_error() -> None:
    """BL-824 AC-4: audio effect on real video-only fixture raises CommandBuildError.

    Creates a real video-only fixture (no audio stream) via FFmpeg, then verifies that
    submitting a render job with a volume audio effect raises CommandBuildError before
    any FFmpeg subprocess is started. Contract: Option A (raise).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        fixture_path = Path(tmpdir) / "video_only.mp4"
        output_path = Path(tmpdir) / "output.mp4"

        _make_video_only_fixture(fixture_path)
        assert fixture_path.exists(), "FFmpeg fixture creation failed"

        vid = _make_video("vid-vonly-001", str(fixture_path))
        clip = _make_clip(
            "clip-vonly-001",
            "vid-vonly-001",
            effects=[{"effect_type": "volume", "parameters": {"volume": 1.5}}],
        )

        clip_repo = AsyncMock()
        clip_repo.list_by_project = AsyncMock(return_value=[clip])

        video_repo = AsyncMock()
        video_repo.get = AsyncMock(return_value=vid)

        registry = EffectRegistry()
        registry.register("volume", VOLUME)

        job = _make_job(str(output_path))

        with pytest.raises(CommandBuildError) as exc_info:
            await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

        error_msg = str(exc_info.value)
        assert "clip-vonly-001" in error_msg, f"Error must name the clip id: {error_msg!r}"
        assert "audio effects" in error_msg, f"Error must mention audio effects: {error_msg!r}"
        assert "no audio stream" in error_msg, f"Error must mention no audio stream: {error_msg!r}"

        # Guard fires BEFORE FFmpeg: output file must not exist
        assert not output_path.exists(), (
            "FFmpeg must not have been invoked (output file must not exist)"
        )
