# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for preview manager helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from stoat_ferret.api.routers.preview import _build_preview_composition
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.preview.manager import PREVIEW_STDERR_MAX_LINES, _truncate_stderr


def test_truncate_stderr_above_cap() -> None:
    """200-line input produces truncated output with the expected marker."""
    lines = [f"line {i:03d}" for i in range(200)]
    result = _truncate_stderr(lines)

    assert "[... 150 lines truncated ...]" in result
    assert len(result.splitlines()) < 60


def test_truncate_stderr_below_cap() -> None:
    """30-line input (below default 50) is returned verbatim."""
    lines = [f"line {i:03d}" for i in range(30)]
    result = _truncate_stderr(lines)

    assert result == "\n".join(lines)
    assert "[... " not in result


def test_truncate_stderr_exactly_cap() -> None:
    """Input at exactly PREVIEW_STDERR_MAX_LINES is returned verbatim."""
    lines = [f"line {i:03d}" for i in range(PREVIEW_STDERR_MAX_LINES)]
    result = _truncate_stderr(lines)

    assert result == "\n".join(lines)
    assert "[... " not in result


def test_truncate_stderr_tail_preserved() -> None:
    """The last line of a long input appears in the truncated output."""
    banner = [f"ffmpeg version banner line {i}" for i in range(100)]
    error_lines = ["Error: something went wrong", "Exit code: 1"]
    lines = banner + error_lines
    result = _truncate_stderr(lines)

    assert "Error: something went wrong" in result
    assert "Exit code: 1" in result
    assert "[... " in result


# ---------- _build_preview_composition (FR-003-AC-1) ----------


async def test_build_preview_composition_single_file_clip() -> None:
    """_build_preview_composition returns the expected structure for a single file clip."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
        transitions=None,
    )
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id="vid-1",
        in_point=0,
        out_point=300,
        timeline_position=0,
        timeline_start=0.0,
        timeline_end=10.0,
        created_at=now,
        updated_at=now,
        clip_type="file",
    )

    video_stub = MagicMock()
    video_stub.path = "/videos/test.mp4"
    video_stub.frame_rate = 30.0

    video_repo = MagicMock()
    video_repo.get = AsyncMock(return_value=video_stub)

    (
        input_paths,
        clip_types,
        in_point_secs,
        filter_complex_str,
        output_fps,
    ) = await _build_preview_composition(
        [clip],
        project,
        video_repo=video_repo,
        asset_repo=None,
        effect_registry=None,
    )

    assert input_paths == ["/videos/test.mp4"]
    assert clip_types == ["file"]
    assert len(in_point_secs) == 1
    assert in_point_secs[0] == 0.0
    assert isinstance(filter_complex_str, str)
    assert output_fps == 30.0
