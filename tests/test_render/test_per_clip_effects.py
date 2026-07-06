# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for per-clip effect parameter extraction in the render worker (BL-615).

Verifies that build_command_for_job passes only the nested parameters dict to
defn.build_fn(), not the full stored effect_data object.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import create_default_registry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job

_PROJECT_ID = "proj-effects-001"
_OUTPUT_PATH = "/renders/effects_output.mp4"


def _make_render_plan() -> str:
    return json.dumps(
        {
            "total_duration": 10.0,
            "settings": {
                "codec": "libx264",
                "fps": 30.0,
                "width": 1920,
                "height": 1080,
                "quality_preset": "standard",
            },
        }
    )


def _make_job() -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-effects-001",
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


def _make_clip(
    clip_id: str,
    video_id: str,
    timeline_position: int,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=0,
        out_point=150,  # 5 seconds at 30 fps
        timeline_position=timeline_position,
        created_at=now,
        updated_at=now,
        effects=effects,
    )


def _make_video(video_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=video_id,
        path=path,
        filename=f"{video_id}.mp4",
        duration_frames=1800,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=50_000_000,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_blur_effect_uses_user_sigma() -> None:
    """BL-615-AC-2: build_fn receives only the parameters dict, not the full effect_data.

    The stored effect_data structure is:
      {"effect_type": "blur", "parameters": {"sigma": 7.0}, "filter_string": "..."}

    Before the fix, build_fn(effect_data) finds no top-level "sigma" key and falls
    back to the default sigma=2.0, producing gblur=sigma=2.
    After the fix, build_fn(effect_data.get("parameters", {})) receives {"sigma": 7.0}
    and produces gblur=sigma=7.
    """
    blur_effect_data: dict[str, Any] = {
        "effect_type": "blur",
        "parameters": {"sigma": 7.0},
        "filter_string": "gblur=sigma=7",
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0, effects=[blur_effect_data]),
        _make_clip("clip-b", "vid-b", timeline_position=150),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    registry = create_default_registry()
    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    # User-specified sigma=7.0 must appear; the default sigma=2.0 must not be the only value
    assert "sigma=7" in filter_complex, (
        f"Expected gblur=sigma=7 in filter_complex but got:\n{filter_complex}"
    )
    # Confirm the default was NOT substituted (sigma=2 from default parameters)
    assert "sigma=2" not in filter_complex, (
        f"Default sigma=2 found in filter_complex — parameter extraction bug still present:\n"
        f"{filter_complex}"
    )


@pytest.mark.asyncio
async def test_opacity_effect_uses_user_value() -> None:
    """BL-615-AC-2 (opacity): build_fn receives only the parameters dict.

    The stored effect_data for opacity=0.25 is:
      {"effect_type": "opacity", "parameters": {"opacity": 0.25}, "filter_string": "..."}

    Before the fix: build_fn(effect_data) returns default opacity=1.0 (full alpha).
    After the fix: build_fn({"opacity": 0.25}) returns the user's value.
    """
    opacity_effect_data: dict[str, Any] = {
        "effect_type": "opacity",
        "parameters": {"opacity": 0.25},
        "filter_string": "colorchannelmixer=aa=0.25",
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0, effects=[opacity_effect_data]),
        _make_clip("clip-b", "vid-b", timeline_position=150),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    registry = create_default_registry()
    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    # User-specified opacity=0.25 must appear in the filter string
    assert "0.25" in filter_complex, (
        f"Expected opacity=0.25 in filter_complex but got:\n{filter_complex}"
    )
