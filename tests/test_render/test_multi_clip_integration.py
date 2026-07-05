# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Integration test for multi-clip rendering via RenderGraphTranslator (BL-505).

Verifies that build_command_for_job produces a valid filter_complex-based FFmpeg
command when a project has multiple clips, with no FFmpeg execution required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import EffectDefinition
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job

_PROJECT_ID = "proj-multi-001"
_OUTPUT_PATH = "/renders/multi_output.mp4"


def _make_render_plan() -> str:
    import json

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
        id="job-multi-001",
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
async def test_multi_clip_render_integration() -> None:
    """BL-505-AC-1/AC-7: build_command_for_job uses RenderGraphTranslator for multi-clip.

    Verifies:
    - Multiple -i inputs (one per clip) are present.
    - -filter_complex is present and contains expected FFmpeg filter structure.
    - -map [final] is present for the video output.
    - -c:v codec flag is present.
    - Output path is the last argument.
    - No FFmpeg execution is required; the translator runs in pure Rust.
    """
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0),
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

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    assert isinstance(cmd, list)
    assert cmd[0] == "ffmpeg"

    # Both video inputs must appear
    input_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
    assert "/media/clip_a.mp4" in input_flags
    assert "/media/clip_b.mp4" in input_flags

    # filter_complex must be present and contain valid FFmpeg filter structure
    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]
    assert isinstance(filter_complex, str)
    assert len(filter_complex) > 0
    # Translator output uses [0:v] and [1:v] stream specifiers
    assert "[0:v]" in filter_complex
    assert "[1:v]" in filter_complex
    # Terminal output label is [final]
    assert "[final]" in filter_complex

    # -map [final] must be present to select the video output
    assert "-map" in cmd
    map_idx = cmd.index("-map")
    assert cmd[map_idx + 1] == "[final]"

    # Standard codec flags
    assert "-c:v" in cmd
    assert "libx264" in cmd

    # Output path must be last
    assert cmd[-1] == _OUTPUT_PATH


@pytest.mark.asyncio
async def test_multi_clip_clip_sort_order() -> None:
    """BL-505: clips are passed to translator in timeline_position order.

    The clip_repository returns clips sorted by timeline_position.
    The multi-clip command must reflect that order in -i arguments.
    """
    # Clips in reverse insertion order — repository will return sorted
    clips = [
        _make_clip("clip-first", "vid-first", timeline_position=0),
        _make_clip("clip-second", "vid-second", timeline_position=150),
    ]
    videos = {
        "vid-first": _make_video("vid-first", "/media/first.mp4"),
        "vid-second": _make_video("vid-second", "/media/second.mp4"),
    }

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)  # already sorted by repo

    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    # First -i must be the first clip's video (timeline_position=0)
    first_i_idx = cmd.index("-i")
    assert cmd[first_i_idx + 1] == "/media/first.mp4"

    # Second -i must be the second clip's video (timeline_position=150)
    second_i_idx = cmd.index("-i", first_i_idx + 1)
    assert cmd[second_i_idx + 1] == "/media/second.mp4"


@pytest.mark.asyncio
async def test_multi_clip_real_effects_fetched_from_registry() -> None:
    """BL-553-AC-1/AC-2: worker fetches real per-clip effects and calls translator.

    Verifies:
    - Worker iterates ALL clips, not just clips[0].
    - Per-clip effects are resolved via the effect registry and passed to translator.
    - Unknown effect_type falls back to RenderEffect.none() without crashing.
    - The resulting command still contains valid filter_complex and -i inputs.
    """
    blur_filter_str = "boxblur=luma_radius=5:luma_power=1"

    def _blur_build_fn(params: dict[str, Any]) -> str:
        return blur_filter_str

    blur_defn = MagicMock(spec=EffectDefinition)
    blur_defn.build_fn = _blur_build_fn

    registry = EffectRegistry()
    registry.register("blur", blur_defn)

    # Clip A has a known blur effect; clip B has an unknown effect type
    clips = [
        _make_clip(
            "clip-a",
            "vid-a",
            timeline_position=0,
            effects=[{"effect_type": "blur", "parameters": {"radius": 5}}],
        ),
        _make_clip(
            "clip-b",
            "vid-b",
            timeline_position=150,
            effects=[{"effect_type": "unknown_effect", "parameters": {}}],
        ),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)

    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert isinstance(cmd, list)
    assert cmd[0] == "ffmpeg"

    # Both clips must appear in -i args (worker iterates ALL clips)
    input_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
    assert "/media/clip_a.mp4" in input_flags
    assert "/media/clip_b.mp4" in input_flags

    # filter_complex must be present (translator was called)
    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]
    assert isinstance(filter_complex, str)
    assert len(filter_complex) > 0
    assert "boxblur" in filter_complex

    # Output path must be last
    assert cmd[-1] == _OUTPUT_PATH
