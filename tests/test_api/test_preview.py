# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for preview-quality observability: reverb multi-clip warning (BL-889) and exception narrowing (BL-890)."""  # noqa: E501

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import CONVOLUTION_REVERB
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import CommandBuildError, build_command_for_job

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_PROJ = "proj-preview-test"
_OUTPUT = "/renders/out.mp4"


def _make_plan(total_duration: float = 30.0) -> str:
    return json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "output_format": "mp4",
                "width": 1920,
                "height": 1080,
                "codec": "libx264",
                "quality_preset": "standard",
                "fps": 30.0,
            },
        }
    )


def _make_job() -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-preview-test",
        project_id=_PROJ,
        status=RenderStatus.RUNNING,
        output_path=_OUTPUT,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_plan(),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_clip(
    cid: str,
    vid_id: str,
    *,
    effects: list[Any] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=cid,
        project_id=_PROJ,
        source_video_id=vid_id,
        in_point=0,
        out_point=900,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type="file",
        effects=effects,
        source_asset_id=None,
        generator_params=None,
    )


def _make_video(vid_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=vid_id,
        path=path,
        filename="source.mp4",
        duration_frames=1800,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=100_000_000,
        created_at=now,
        updated_at=now,
        audio_codec="aac",
    )


def _make_clip_repo(*clips: Clip) -> AsyncMock:
    r: AsyncMock = AsyncMock()
    r.list_by_project = AsyncMock(return_value=list(clips))
    return r


def _make_video_repo(*videos: Video) -> AsyncMock:
    vid_map = {v.id: v for v in videos}
    r: AsyncMock = AsyncMock()

    async def _get(vid_id: str) -> Video | None:
        return vid_map.get(vid_id)

    r.get = AsyncMock(side_effect=_get)
    return r


# ---------------------------------------------------------------------------
# BL-889: reverb multi-clip warning tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reverb_multiclip_emits_warning() -> None:
    """FR-001-AC-1/AC-2: warning emitted before CommandBuildError for multi-clip reverb (BL-889)."""
    vid_a = _make_video("vid-mc-ra", "/media/ra.mp4")
    vid_b = _make_video("vid-mc-rb", "/media/rb.mp4")
    clip_a = _make_clip(
        "clip-mc-ra",
        "vid-mc-ra",
        effects=[
            {
                "effect_type": "convolution_reverb",
                "parameters": {"ir_name": "hall_small", "mix": 0.4},
            }
        ],
    )
    clip_b = _make_clip("clip-mc-rb", "vid-mc-rb")
    reg = EffectRegistry()
    reg.register("convolution_reverb", CONVOLUTION_REVERB)

    err_match = "multi-clip convolution_reverb is not yet supported"
    with (
        patch("stoat_ferret.render.worker.logger") as mock_logger,
        pytest.raises(CommandBuildError, match=err_match),
    ):
        await build_command_for_job(
            _make_job(),
            _make_clip_repo(clip_a, clip_b),
            _make_video_repo(vid_a, vid_b),
            effect_registry=reg,
        )

    mock_logger.warning.assert_called_once_with(
        "multi-clip convolution_reverb is not supported; failing closed",
        clip_count=2,
        effect="convolution_reverb",
    )


@pytest.mark.asyncio
async def test_reverb_single_clip_no_warning() -> None:
    """FR-002-AC-2: single-clip convolution_reverb does NOT emit the multi-clip warning (BL-889)."""
    vid = _make_video("vid-sc-r", "/media/sr.mp4")
    clip = _make_clip(
        "clip-sc-r",
        "vid-sc-r",
        effects=[
            {
                "effect_type": "convolution_reverb",
                "parameters": {"ir_name": "hall_small", "mix": 0.4},
            }
        ],
    )
    reg = EffectRegistry()
    reg.register("convolution_reverb", CONVOLUTION_REVERB)

    with patch("stoat_ferret.render.worker.logger") as mock_logger:
        # Single-clip path succeeds — IR WAV wiring is handled by the single-clip command builder
        await build_command_for_job(
            _make_job(),
            _make_clip_repo(clip),
            _make_video_repo(vid),
            effect_registry=reg,
        )

    warning_event_names = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert (
        "multi-clip convolution_reverb is not supported; failing closed" not in warning_event_names
    )


# ---------------------------------------------------------------------------
# BL-890: preview exception narrowing tests
# ---------------------------------------------------------------------------


def test_unexpected_exception_propagates() -> None:
    """BL-890-AC-1/AC-2: RuntimeError propagates out of _build_preview_render_effects."""
    from unittest.mock import MagicMock, patch

    from stoat_ferret.api.routers.preview import _build_preview_render_effects

    clip = MagicMock()
    clip.id = "clip-exc-test"
    effect_registry = MagicMock()

    # Patch at the source since _build_preview_render_effects does a local import
    with (
        patch(
            "stoat_ferret.render.worker._build_clip_render_effects",
            side_effect=RuntimeError("unexpected internal error"),
        ),
        pytest.raises(RuntimeError, match="unexpected internal error"),
    ):
        _build_preview_render_effects(clip, effect_registry)


def test_command_build_error_still_graceful() -> None:
    """BL-890-AC-2: CommandBuildError (preview-unsupported effect) is still gracefully skipped."""
    from unittest.mock import MagicMock, patch

    from stoat_ferret.api.routers.preview import _build_preview_render_effects
    from stoat_ferret.render.worker import CommandBuildError

    clip = MagicMock()
    clip.id = "clip-cbe-test"
    effect_registry = MagicMock()

    # Patch at the source since _build_preview_render_effects does a local import
    with patch(
        "stoat_ferret.render.worker._build_clip_render_effects",
        side_effect=CommandBuildError("multi-clip convolution_reverb is not yet supported"),
    ):
        result = _build_preview_render_effects(clip, effect_registry)

    # Should return [RenderEffect.none()] gracefully — not propagate
    assert len(result) == 1
