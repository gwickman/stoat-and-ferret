# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_unknown_effect_failclosed — fail-closed contract (BL-795).

Asserts that submitting a render job with an unknown effect type causes CommandBuildError
to be raised at build time, before any FFmpeg invocation. No STOAT_TEST_FFMPEG gate
required: the error is raised during command construction, not FFmpeg execution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import CommandBuildError, build_command_for_job

_PROJECT_ID = "proj-failclosed-001"
_OUTPUT_PATH = "/renders/failclosed_output.mp4"


def _make_render_plan() -> str:
    return json.dumps(
        {
            "total_duration": 3.0,
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


def _make_job() -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-failclosed-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=_OUTPUT_PATH,
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


@pytest.mark.asyncio
async def test_unknown_effect_raises_command_build_error_before_ffmpeg() -> None:
    """BL-795 AC-1/AC-2: unknown effect type raises CommandBuildError at build time.

    Verifies the fail-closed contract: a clip referencing an unregistered effect type
    causes CommandBuildError before FFmpeg is invoked, naming both the effect type and
    clip id in the error message. No STOAT_TEST_FFMPEG required.
    """
    vid = _make_video("vid-fc-001", "/media/fixture.mp4")
    clip = _make_clip(
        "clip-fc-001",
        "vid-fc-001",
        effects=[{"effect_type": "totally_unknown_effect_xyz", "parameters": {}}],
    )

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip])

    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=vid)

    # Use a registry that does NOT contain the effect type
    registry = EffectRegistry()

    job = _make_job()

    with pytest.raises(CommandBuildError) as exc_info:
        await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    error_msg = str(exc_info.value)
    assert "totally_unknown_effect_xyz" in error_msg, (
        f"Error must name the effect type: {error_msg!r}"
    )
    assert "clip-fc-001" in error_msg, f"Error must name the clip id: {error_msg!r}"
