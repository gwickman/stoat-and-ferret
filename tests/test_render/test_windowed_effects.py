# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for windowed effect dispatch in the render worker (BL-512).

Tests that:
- windowed_custom() is dispatched when effect has window AND timeline_T_capable=True
- custom() is dispatched when no window present (regardless of T-capability)
- custom() is dispatched when effect is non-T-capable (window silently ignored)
- BL-512-AC-4 stub test for deferred non-T fallback
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import EffectDefinition
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job

_PROJECT_ID = "proj-windowed-001"
_OUTPUT_PATH = "/renders/windowed_output.mp4"


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
        id="job-windowed-001",
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
async def test_windowed_custom_dispatch_t_capable() -> None:
    """Worker dispatches windowed_custom() for T-capable effect with window.

    When effect_data contains a 'window' key AND the EffectDefinition has
    timeline_T_capable=True, the worker must call RenderEffect.windowed_custom(),
    causing translate.rs to emit :enable='between(t,s,e)' in the filter_complex.
    """
    effect_data: dict[str, Any] = {
        "effect_type": "hue_windowed",
        "parameters": {},
        "window": {"start_s": 1.0, "end_s": 3.0},
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0, effects=[effect_data]),
        _make_clip("clip-b", "vid-b", timeline_position=150),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    defn = MagicMock(spec=EffectDefinition)
    defn.build_fn = lambda params: "hue=s=0"
    defn.timeline_T_capable = True

    registry = EffectRegistry()
    registry.register("hue_windowed", defn)

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    # translate.rs Custom branch must emit :enable='between(t,1.0,3.0)' for windowed T-capable
    assert "enable='between(t," in filter_complex, (
        f"Expected enable='between(t,...) in filter_complex but got:\n{filter_complex}"
    )
    assert "between(t,1.0,3.0)" in filter_complex, (
        f"Expected between(t,1.0,3.0) in filter_complex but got:\n{filter_complex}"
    )


@pytest.mark.asyncio
async def test_no_window_dispatch_uses_custom() -> None:
    """Effect without window dispatches RenderEffect.custom() — no enable= in filter_complex."""
    effect_data: dict[str, Any] = {
        "effect_type": "blur_no_window",
        "parameters": {"sigma": 3.0},
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0, effects=[effect_data]),
        _make_clip("clip-b", "vid-b", timeline_position=150),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    defn = MagicMock(spec=EffectDefinition)
    defn.build_fn = lambda params: f"gblur=sigma={params.get('sigma', 2.0)}"
    defn.timeline_T_capable = True  # T-capable, but no window key in effect_data

    registry = EffectRegistry()
    registry.register("blur_no_window", defn)

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    # No window key → custom() used → no enable= in filter_complex
    assert "enable='between" not in filter_complex, (
        f"Unexpected enable='between(t,...) in filter_complex (no window key):\n{filter_complex}"
    )
    assert "gblur=sigma=3.0" in filter_complex, (
        f"Expected gblur=sigma=3.0 in filter_complex but got:\n{filter_complex}"
    )


@pytest.mark.asyncio
async def test_non_t_capable_effect_ignores_window() -> None:
    """Non-T-capable effect with window routes through split/trim/concat (BL-512-AC-2).

    The effect chain (scale=iw:ih) must appear in the filter_complex output and
    no enable='between(t,...) expression may be emitted. The graph-level windowing
    (split/trim/concat) is verified by test_nont_window_fallback_split_trim_concat.
    """
    effect_data: dict[str, Any] = {
        "effect_type": "scale_windowed",
        "parameters": {},
        "window": {"start_s": 0.5, "end_s": 2.0},
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0, effects=[effect_data]),
        _make_clip("clip-b", "vid-b", timeline_position=150),
    ]
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4"),
    }

    defn = MagicMock(spec=EffectDefinition)
    defn.build_fn = lambda params: "scale=iw:ih"
    defn.timeline_T_capable = False  # scale is NOT T-capable

    registry = EffectRegistry()
    registry.register("scale_windowed", defn)

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    # Non-T-capable: window silently ignored, custom() used, no enable= emitted
    assert "enable='between" not in filter_complex, (
        f"Non-T-capable effect must not emit enable='between(t,...), but got:\n{filter_complex}"
    )
    assert "scale=iw:ih" in filter_complex, (
        f"Expected scale=iw:ih in filter_complex but got:\n{filter_complex}"
    )


@pytest.mark.asyncio
async def test_nont_window_fallback_split_trim_concat() -> None:
    """BL-512-AC-4: Non-T windowed effect routes through split/trim/concat.

    A non-T-capable effect (e.g. scale) with a window must produce
    split/trim/concat parts in the filter_complex instead of enable='between(t,...)'.
    The window bounds are respected at the graph level by splitting the clip,
    applying the effect only to the [start_s, end_s] segment, and concatenating
    the three segments.
    """
    effect_data: dict[str, Any] = {
        "effect_type": "scale_nont_windowed",
        "parameters": {},
        "window": {"start_s": 1.0, "end_s": 3.0},
    }
    clips = [
        _make_clip("clip-x", "vid-x", timeline_position=0, effects=[effect_data]),
    ]
    videos = {
        "vid-x": _make_video("vid-x", "/media/clip_x.mp4"),
    }

    defn = MagicMock(spec=EffectDefinition)
    defn.build_fn = lambda params: "scale=iw*0.5:ih*0.5"
    defn.timeline_T_capable = False  # scale is NOT T-capable

    registry = EffectRegistry()
    registry.register("scale_nont_windowed", defn)

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    job = _make_job()
    cmd = await build_command_for_job(job, clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    # Non-T fallback: split/trim/concat must appear, not enable='between'
    assert "split=3" in filter_complex, (
        f"Non-T windowed effect must use split=3, got:\n{filter_complex}"
    )
    assert "trim" in filter_complex, f"Non-T windowed effect must use trim, got:\n{filter_complex}"
    assert "concat=n=3" in filter_complex, (
        f"Non-T windowed effect must use concat=n=3, got:\n{filter_complex}"
    )
    assert "enable='between" not in filter_complex, (
        f"Non-T effect must not emit enable='between(t,...)', got:\n{filter_complex}"
    )
    # Effect chain must appear inside the windowed segment
    assert "scale=iw*0.5:ih*0.5" in filter_complex, (
        f"Effect must appear in filter_complex segment, got:\n{filter_complex}"
    )
