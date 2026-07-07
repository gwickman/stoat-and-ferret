# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for single-clip windowed effect dispatch in build_command_for_job (BL-616).

Tests that the single-clip translator path dispatches windowed_custom() when an effect
carries a window key and timeline_T_capable is True, mirroring the multi-clip path.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import EffectDefinition
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import build_command_for_job

_NOW = datetime.now(timezone.utc)
_PROJECT_ID = "proj-windowed-sc-001"
_OUTPUT_PATH = "/renders/windowed_sc_output.mp4"

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)


def _make_render_plan(total_duration: float = 10.0) -> str:
    return json.dumps(
        {
            "total_duration": total_duration,
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
    return RenderJob(
        id="job-windowed-sc-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=_OUTPUT_PATH,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_render_plan(),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )


def _make_single_clip(
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    return Clip(
        id="clip-sc-wind-001",
        project_id=_PROJECT_ID,
        source_video_id="vid-sc-wind-001",
        in_point=0,
        out_point=300,  # 10 seconds at 30 fps
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
        effects=effects,
    )


def _make_video(audio_codec: str | None = "aac") -> Video:
    return Video(
        id="vid-sc-wind-001",
        path="/media/single_clip.mp4",
        filename="single_clip.mp4",
        duration_frames=300,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        audio_codec=audio_codec,
        file_size=10_000_000,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_repos(
    clip: Clip,
    video: Video,
) -> tuple[AsyncMock, AsyncMock]:
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=video)
    return clip_repo, video_repo


def _make_t_capable_registry(effect_type: str, filter_str: str) -> EffectRegistry:
    defn = MagicMock(spec=EffectDefinition)
    defn.build_fn = lambda params: filter_str
    defn.timeline_T_capable = True
    registry = EffectRegistry()
    registry.register(effect_type, defn)
    return registry


def _make_non_t_capable_registry(effect_type: str, filter_str: str) -> EffectRegistry:
    defn = MagicMock(spec=EffectDefinition)
    defn.build_fn = lambda params: filter_str
    defn.timeline_T_capable = False
    registry = EffectRegistry()
    registry.register(effect_type, defn)
    return registry


# ---------------------------------------------------------------------------
# AC-1: Single-clip T-capable effect with window → windowed_custom() dispatched
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_clip_windowed_t_capable_emits_enable() -> None:
    """BL-616-AC-1: single-clip T-capable effect + window → enable='between(t,1.0,3.0)'.

    Verifies that build_command_for_job dispatches windowed_custom() for a single-clip
    project with a T-capable effect (gblur) carrying window {start_s:1.0, end_s:3.0},
    and that the emitted filter_complex includes enable='between(t,1.0,3.0)'.
    """
    effect_data: dict[str, Any] = {
        "effect_type": "gblur",
        "parameters": {"sigma": 2.0},
        "window": {"start_s": 1.0, "end_s": 3.0},
    }
    clip = _make_single_clip(effects=[effect_data])
    video = _make_video()
    clip_repo, video_repo = _make_repos(clip, video)
    registry = _make_t_capable_registry("gblur", "gblur=sigma=2.0")

    cmd = await build_command_for_job(_make_job(), clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd, "Expected -filter_complex flag in command"
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    assert "enable='between(t," in filter_complex, (
        f"Expected enable='between(t,...) in filter_complex for windowed T-capable effect, "
        f"got:\n{filter_complex}"
    )
    assert "between(t,1.0,3.0)" in filter_complex, (
        f"Expected between(t,1.0,3.0) in filter_complex, got:\n{filter_complex}"
    )


# ---------------------------------------------------------------------------
# AC-2: Single-clip non-T-capable effect with window → custom() used, no enable=
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_clip_non_t_capable_with_window_no_enable() -> None:
    """BL-616-AC-2: single-clip non-T-capable effect + window → no enable=, no crash.

    Mirrors the multi-clip else branch: when timeline_T_capable=False, the window
    key is silently ignored and RenderEffect.custom() is used instead.
    """
    effect_data: dict[str, Any] = {
        "effect_type": "scale",
        "parameters": {},
        "window": {"start_s": 0.5, "end_s": 2.0},
    }
    clip = _make_single_clip(effects=[effect_data])
    video = _make_video()
    clip_repo, video_repo = _make_repos(clip, video)
    registry = _make_non_t_capable_registry("scale", "scale=iw:ih")

    cmd = await build_command_for_job(_make_job(), clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd, "Expected -filter_complex flag in command"
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    assert "enable='between" not in filter_complex, (
        f"Non-T-capable effect must not emit enable='between(t,...), got:\n{filter_complex}"
    )
    assert "scale=iw:ih" in filter_complex, (
        f"Expected scale=iw:ih filter string in filter_complex, got:\n{filter_complex}"
    )


# ---------------------------------------------------------------------------
# AC-4: Existing single-clip renders without window still pass (regression)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_clip_no_window_unaffected() -> None:
    """BL-616-AC-4: single-clip effect without window key continues using custom().

    Regression guard: adding the window_sc check must not affect effects that
    don't carry a window key.
    """
    effect_data: dict[str, Any] = {
        "effect_type": "gblur",
        "parameters": {"sigma": 3.0},
        # no 'window' key
    }
    clip = _make_single_clip(effects=[effect_data])
    video = _make_video()
    clip_repo, video_repo = _make_repos(clip, video)
    registry = _make_t_capable_registry("gblur", "gblur=sigma=3.0")

    cmd = await build_command_for_job(_make_job(), clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    assert "enable='between" not in filter_complex, (
        f"No window key → must not emit enable='between(t,...), got:\n{filter_complex}"
    )
    assert "gblur=sigma=3.0" in filter_complex, (
        f"Expected gblur=sigma=3.0 in filter_complex, got:\n{filter_complex}"
    )


@pytest.mark.asyncio
async def test_single_clip_no_effects_no_window() -> None:
    """BL-616-AC-4: single-clip with no effects produces a valid command (regression)."""
    clip = _make_single_clip(effects=None)
    video = _make_video()
    clip_repo, video_repo = _make_repos(clip, video)

    cmd = await build_command_for_job(_make_job(), clip_repo, video_repo)

    assert "ffmpeg" in cmd
    assert _OUTPUT_PATH in cmd
    assert "enable='between" not in " ".join(cmd)


# ---------------------------------------------------------------------------
# AC-3: FFmpeg-gated single-clip windowed render probe
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_single_clip_windowed_render_probe_ffmpeg() -> None:
    """BL-616-AC-3 (FFmpeg-gated): single-clip windowed T-capable effect emits enable= in command.

    Discharge command (STOAT_TEST_FFMPEG=1):
        uv run pytest tests/test_render/test_worker_windowed_dispatch.py \
        ::test_single_clip_windowed_render_probe_ffmpeg -v

    This test verifies the filter_complex string contains enable= when STOAT_TEST_FFMPEG=1.
    A full render-and-ffprobe test is out of scope for this command-builder unit test;
    the render integration is covered by the command-level assertion.
    """
    effect_data: dict[str, Any] = {
        "effect_type": "gblur",
        "parameters": {"sigma": 2.0},
        "window": {"start_s": 1.0, "end_s": 4.0},
    }
    clip = _make_single_clip(effects=[effect_data])
    video = _make_video()
    clip_repo, video_repo = _make_repos(clip, video)
    registry = _make_t_capable_registry("gblur", "gblur=sigma=2.0")

    cmd = await build_command_for_job(_make_job(), clip_repo, video_repo, effect_registry=registry)

    assert "-filter_complex" in cmd
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]

    assert "enable='between(t," in filter_complex, (
        f"FFmpeg-gated: expected enable='between(t,...) in filter_complex, got:\n{filter_complex}"
    )
    assert "between(t,1.0,4.0)" in filter_complex
