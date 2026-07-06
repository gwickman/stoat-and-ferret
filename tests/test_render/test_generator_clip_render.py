# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for generator clip routing in the render worker (BL-604).

Covers:
- _build_generator_source helper (unit)
- Multi-clip and single-clip command structure for generator clips
- STOAT_TEST_FFMPEG-gated end-to-end render tests
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import (
    CommandBuildError,
    _build_generator_source,
    build_command_for_job,
)

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")
_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)

_PROJECT_ID = "proj-gen-001"
_LAVFI_COLOR = "color=c=blue:s=320x240:r=30:d=3"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_render_job(output_path: str, total_duration: float = 3.0) -> RenderJob:
    now = datetime.now(timezone.utc)
    plan = json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "codec": "libx264",
                "fps": 30.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
            },
        }
    )
    return RenderJob(
        id="job-gen-001",
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


def _make_generator_clip(
    clip_id: str,
    timeline_position: int,
    lavfi_string: str = _LAVFI_COLOR,
    out_point: int = 90,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=None,
        in_point=0,
        out_point=out_point,
        timeline_position=timeline_position,
        created_at=now,
        updated_at=now,
        clip_type="generator",
        generator_params={"lavfi_string": lavfi_string},
    )


# ---------------------------------------------------------------------------
# Unit tests: _build_generator_source helper
# ---------------------------------------------------------------------------


def test_build_generator_source_returns_lavfi_string() -> None:
    """_build_generator_source returns lavfi_string from generator_params."""
    result = _build_generator_source({"lavfi_string": _LAVFI_COLOR})
    assert result == _LAVFI_COLOR


def test_build_generator_source_missing_key_raises() -> None:
    """_build_generator_source raises CommandBuildError when lavfi_string absent."""
    with pytest.raises(CommandBuildError, match="lavfi_string"):
        _build_generator_source({})


def test_build_generator_source_empty_value_raises() -> None:
    """_build_generator_source raises CommandBuildError for empty lavfi_string."""
    with pytest.raises(CommandBuildError, match="lavfi_string"):
        _build_generator_source({"lavfi_string": ""})


# ---------------------------------------------------------------------------
# Unit tests: command structure (no FFmpeg execution)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generator_clip_multi_clip_command_uses_lavfi_flag() -> None:
    """FR-002: multi-clip generator clip emits -f lavfi -i <lavfi_str> in command."""
    clips = [
        _make_generator_clip("clip-a", timeline_position=0),
        _make_generator_clip("clip-b", timeline_position=90),
    ]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=None)

    job = _make_render_job("/out/result.mp4", total_duration=6.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    assert cmd[0] == "ffmpeg"
    assert "-f" in cmd
    f_idx = cmd.index("-f")
    assert cmd[f_idx + 1] == "lavfi"
    assert cmd[f_idx + 2] == "-t"
    assert cmd[f_idx + 4] == "-i"
    assert cmd[f_idx + 5] == _LAVFI_COLOR
    assert "-filter_complex" in cmd
    assert "-map" in cmd


@pytest.mark.asyncio
async def test_generator_clip_single_clip_command_uses_lavfi_flag() -> None:
    """FR-007: single-clip generator path emits -f lavfi -i <lavfi_str> in command."""
    clips = [_make_generator_clip("clip-a", timeline_position=0)]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=None)

    job = _make_render_job("/out/result.mp4")
    cmd = await build_command_for_job(job, clip_repo, video_repo)

    assert cmd[0] == "ffmpeg"
    assert cmd[1] == "-f"
    assert cmd[2] == "lavfi"
    assert cmd[3] == "-i"
    assert cmd[4] == _LAVFI_COLOR
    assert "-filter_complex" in cmd


@pytest.mark.asyncio
async def test_generator_clip_missing_lavfi_string_raises() -> None:
    """Generator clip with no lavfi_string in generator_params raises CommandBuildError."""
    now = datetime.now(timezone.utc)
    bad_clip = Clip(
        id="clip-bad",
        project_id=_PROJECT_ID,
        source_video_id=None,
        in_point=0,
        out_point=90,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type="generator",
        generator_params={"type": "aevalsrc"},  # no lavfi_string key
    )

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[bad_clip])
    video_repo = AsyncMock()

    job = _make_render_job("/out/result.mp4")
    with pytest.raises(CommandBuildError, match="lavfi_string"):
        await build_command_for_job(job, clip_repo, video_repo)


# ---------------------------------------------------------------------------
# STOAT_TEST_FFMPEG-gated integration tests
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_generator_clip_multi_clip_render(tmp_path: Path) -> None:
    """FR-002-AC-1 = BL-604-AC-2: multi-clip generator project renders non-empty mp4."""
    out = tmp_path / "output.mp4"

    clips = [
        _make_generator_clip("clip-a", 0, lavfi_string="color=c=red:s=320x240:r=30"),
        _make_generator_clip("clip-b", 3, lavfi_string="color=c=green:s=320x240:r=30"),
    ]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=None)

    job = _make_render_job(str(out), total_duration=6.0)
    cmd = await build_command_for_job(job, clip_repo, video_repo)
    cmd.append("-y")

    r = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed: {r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0


@_FFMPEG_SKIP
async def test_generator_clip_single_clip_render(tmp_path: Path) -> None:
    """FR-007-AC-2: single generator clip renders non-empty mp4."""
    out = tmp_path / "output.mp4"

    clips = [_make_generator_clip("clip-a", 0, lavfi_string="color=c=blue:s=320x240:r=30")]

    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()

    job = _make_render_job(str(out))
    cmd = await build_command_for_job(job, clip_repo, video_repo)
    cmd.append("-y")

    r = subprocess.run(cmd, capture_output=True, timeout=60)  # noqa: ASYNC221
    assert r.returncode == 0, f"Render failed: {r.stderr.decode()[-800:]}"
    assert out.exists() and out.stat().st_size > 0
