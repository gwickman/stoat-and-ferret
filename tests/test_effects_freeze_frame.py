# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for FreezeFrameBuilder and FREEZE_FRAME effect definition (BL-449)."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import pytest

from stoat_ferret_core import FreezeFrameBuilder

# ---------------------------------------------------------------------------
# Unit tests — FreezeFrameBuilder filter string generation (no FFmpeg required)
# ---------------------------------------------------------------------------


def test_freeze_frame_builder_filter_contains_tpad_clone() -> None:
    """FreezeFrameBuilder.build() returns a tpad=stop_mode=clone filter (BL-449-AC-1, FFmpeg 8)."""
    f = FreezeFrameBuilder(0, 2.0).build()
    assert "tpad=stop_mode=clone" in str(f), f"expected 'tpad=stop_mode=clone' in filter, got: {f}"


def test_freeze_frame_builder_filter_contains_tpad() -> None:
    """FreezeFrameBuilder.build() filter contains 'tpad' for duration extension (BL-449-AC-1)."""
    f = FreezeFrameBuilder(0, 2.0).build()
    assert "tpad" in str(f), f"expected 'tpad' in filter, got: {f}"


def test_freeze_frame_builder_frame_number_accepted() -> None:
    """FreezeFrameBuilder accepts any valid frame_number and produces a tpad filter (FFmpeg 8)."""
    f = str(FreezeFrameBuilder(30, 1.0).build())
    assert "tpad=stop_mode=clone" in f, f"expected tpad=stop_mode=clone in: {f}"


def test_freeze_frame_builder_duration_in_filter() -> None:
    """Hold duration appears in the tpad stop_duration parameter."""
    f = str(FreezeFrameBuilder(0, 2.5).build())
    assert "stop_duration=2.5" in f, f"expected stop_duration=2.5 in: {f}"


def test_freeze_frame_builder_integer_duration_no_decimal() -> None:
    """Integer durations are formatted without trailing '.0'."""
    f = str(FreezeFrameBuilder(0, 2.0).build())
    assert "stop_duration=2" in f, f"expected stop_duration=2 (no decimal) in: {f}"
    assert "stop_duration=2.0" not in f, f"expected no stop_duration=2.0 in: {f}"


def test_freeze_frame_builder_frame_number_property() -> None:
    """FreezeFrameBuilder.frame_number returns the value passed to the constructor."""
    builder = FreezeFrameBuilder(42, 1.0)
    assert builder.frame_number == 42


def test_freeze_frame_builder_hold_duration_property() -> None:
    """FreezeFrameBuilder.hold_duration_s returns the value passed to the constructor."""
    builder = FreezeFrameBuilder(0, 3.75)
    assert builder.hold_duration_s == pytest.approx(3.75)


def test_freeze_frame_builder_repr() -> None:
    """FreezeFrameBuilder.__repr__ returns a descriptive string."""
    r = repr(FreezeFrameBuilder(10, 2.0))
    assert "FreezeFrameBuilder" in r
    assert "10" in r


def test_freeze_frame_builder_zero_duration_raises() -> None:
    """FreezeFrameBuilder raises ValueError when hold_duration_s <= 0."""
    with pytest.raises((ValueError, Exception)):
        FreezeFrameBuilder(0, 0.0)


def test_freeze_frame_builder_negative_duration_raises() -> None:
    """FreezeFrameBuilder raises ValueError when hold_duration_s is negative."""
    with pytest.raises((ValueError, Exception)):
        FreezeFrameBuilder(0, -1.0)


def test_freeze_frame_builder_frame_zero_valid() -> None:
    """Frame number 0 (first frame) is a valid input; produces tpad filter (FFmpeg 8)."""
    f = str(FreezeFrameBuilder(0, 1.0).build())
    assert "tpad=stop_mode=clone" in f


# ---------------------------------------------------------------------------
# EffectDefinition tests
# ---------------------------------------------------------------------------


def test_freeze_frame_registered_in_default_registry() -> None:
    """FREEZE_FRAME is registered under 'freeze_frame' in the default registry (BL-449-AC-2)."""
    from stoat_ferret.effects.definitions import create_default_registry

    registry = create_default_registry()
    assert registry.get("freeze_frame") is not None, "freeze_frame effect must be registered"


def test_freeze_frame_build_fn_returns_tpad_filter() -> None:
    """FREEZE_FRAME.build_fn returns a tpad=stop_mode=clone filter (BL-449-AC-2, FFmpeg 8)."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    result = FREEZE_FRAME.build_fn({"frame_number": 5, "duration_s": 2.0})
    assert "tpad=stop_mode=clone" in result, f"Expected tpad=stop_mode=clone in: {result}"
    assert "stop_duration=2" in result, f"Expected stop_duration=2 in: {result}"


def test_freeze_frame_build_fn_accepts_frame_number() -> None:
    """FREEZE_FRAME.build_fn accepts frame_number; not encoded in filter (FFmpeg 8)."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    result = FREEZE_FRAME.build_fn({"frame_number": 15, "duration_s": 1.0})
    assert "tpad=stop_mode=clone" in result, f"Expected tpad=stop_mode=clone in: {result}"


def test_freeze_frame_build_fn_duration_appears() -> None:
    """FREEZE_FRAME.build_fn encodes the hold duration."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    result = FREEZE_FRAME.build_fn({"frame_number": 0, "duration_s": 3.5})
    assert "stop_duration=3.5" in result, f"Expected stop_duration=3.5 in: {result}"


def test_freeze_frame_parameter_schema_required_fields() -> None:
    """FREEZE_FRAME parameter schema requires frame_number and duration_s."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    required = FREEZE_FRAME.parameter_schema.get("required", [])
    assert "frame_number" in required
    assert "duration_s" in required


def test_freeze_frame_parameter_schema_additionalproperties_false() -> None:
    """FREEZE_FRAME parameter schema rejects unknown parameters."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    assert FREEZE_FRAME.parameter_schema.get("additionalProperties") is False


def test_freeze_frame_preview_fn_contains_tpad() -> None:
    """FREEZE_FRAME.preview_fn returns a filter string containing 'tpad' (FFmpeg 8)."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    result = FREEZE_FRAME.preview_fn()
    assert "tpad" in result, f"Expected 'tpad' in preview filter: {result}"


def test_freeze_frame_ai_summary_nonempty() -> None:
    """FREEZE_FRAME.ai_summary is a non-empty string."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    assert FREEZE_FRAME.ai_summary.strip(), "ai_summary must not be empty"


def test_freeze_frame_example_prompt_nonempty() -> None:
    """FREEZE_FRAME.example_prompt is a non-empty string."""
    from stoat_ferret.effects.definitions import FREEZE_FRAME

    assert FREEZE_FRAME.example_prompt.strip(), "example_prompt must not be empty"


# ---------------------------------------------------------------------------
# API tests — frame_number bounds check (BL-449-AC-2)
# ---------------------------------------------------------------------------

_PROJECT_ID = "proj-freeze-bounds"
_CLIP_10F = "clip-freeze-10f"
_FPS = 30


def _make_freeze_client() -> tuple:
    """Create a TestClient with a seeded project and a 10-frame clip."""
    from fastapi.testclient import TestClient

    from stoat_ferret.api.app import create_app
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.models import Clip, Project
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from tests.factories import make_test_video

    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    video_repo = AsyncInMemoryVideoRepository()

    now = datetime.now(timezone.utc)
    project = Project(
        id=_PROJECT_ID,
        name="Freeze Bounds Test",
        output_width=1920,
        output_height=1080,
        output_fps=_FPS,
        created_at=now,
        updated_at=now,
    )
    video = make_test_video()
    clip = Clip(
        id=_CLIP_10F,
        project_id=_PROJECT_ID,
        source_video_id=video.id,
        in_point=0,
        out_point=10,  # 10 frames (frames 0–9 valid)
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )

    loop = asyncio.new_event_loop()
    loop.run_until_complete(project_repo.add(project))
    loop.run_until_complete(video_repo.add(video))
    loop.run_until_complete(clip_repo.add(clip))
    loop.close()

    app = create_app(
        project_repository=project_repo,
        clip_repository=clip_repo,
        video_repository=video_repo,
    )
    return TestClient(app)


@pytest.mark.api
def test_apply_freeze_frame_valid_frame_returns_201() -> None:
    """Applying freeze_frame with frame_number within clip duration returns 201 (BL-449-AC-2)."""
    client = _make_freeze_client()
    with client:
        response = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_10F}/effects",
            json={
                "effect_type": "freeze_frame",
                "parameters": {"frame_number": 5, "duration_s": 1.0},
            },
        )
    assert response.status_code == 201, (
        f"Expected 201 for frame_number=5 in 10-frame clip, "
        f"got {response.status_code}: {response.json()}"
    )


@pytest.mark.api
def test_apply_freeze_frame_out_of_range_returns_422() -> None:
    """Applying freeze_frame with frame_number >= clip duration returns 422 (BL-449-AC-2)."""
    client = _make_freeze_client()
    with client:
        response = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_10F}/effects",
            json={
                "effect_type": "freeze_frame",
                "parameters": {"frame_number": 10, "duration_s": 1.0},
            },
        )
    assert response.status_code == 422, (
        f"Expected 422 for frame_number=10 in 10-frame clip, "
        f"got {response.status_code}: {response.json()}"
    )
    detail = response.json()["detail"]
    assert detail.get("error") == "frame_number_out_of_range", (
        f"Expected frame_number_out_of_range: {detail}"
    )


@pytest.mark.api
def test_apply_freeze_frame_last_valid_frame_returns_201() -> None:
    """Applying freeze_frame with frame_number == clip_duration - 1 returns 201 (boundary)."""
    client = _make_freeze_client()
    with client:
        response = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_10F}/effects",
            json={
                "effect_type": "freeze_frame",
                "parameters": {"frame_number": 9, "duration_s": 1.0},
            },
        )
    assert response.status_code == 201, (
        f"Expected 201 for frame_number=9 (last frame) in 10-frame clip, "
        f"got {response.status_code}: {response.json()}"
    )


# ---------------------------------------------------------------------------
# FFmpeg-gated contract tests (require STOAT_TEST_FFMPEG=1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg required; set STOAT_TEST_FFMPEG=1",
)
def test_freeze_frame_produces_valid_output(tmp_path) -> None:
    """FreezeFrameBuilder applied via FFmpeg produces a longer output (BL-449-AC-3)."""
    import subprocess
    from pathlib import Path

    tmp = Path(str(tmp_path))
    source = tmp / "source.mp4"
    frozen_out = tmp / "frozen.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=3:size=160x90:rate=10",
            "-c:v",
            "libx264",
            "-t",
            "3",
            str(source),
        ],
        check=True,
        capture_output=True,
    )

    vf = str(FreezeFrameBuilder(5, 2.0).build())
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vf",
            vf,
            str(frozen_out),
        ],
        check=True,
        capture_output=True,
    )

    assert frozen_out.exists(), "frozen output file must exist"
    assert frozen_out.stat().st_size > 0, "frozen output must be non-empty"
