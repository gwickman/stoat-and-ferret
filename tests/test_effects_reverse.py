# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for ReverseBuilder and REVERSE effect definition (BL-444)."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret_core import ReverseBuilder

# ---------------------------------------------------------------------------
# Unit tests — ReverseBuilder filter string generation (no FFmpeg required)
# ---------------------------------------------------------------------------


def test_reverse_builder_video_filter_name() -> None:
    """ReverseBuilder().video_filter() returns Filter with 'reverse' in its string (BL-444-AC-1)."""
    f = ReverseBuilder().video_filter()
    assert "reverse" in str(f), f"expected 'reverse' in video filter, got: {f}"


def test_reverse_builder_audio_filter_name() -> None:
    """ReverseBuilder().audio_filter() returns a Filter with 'areverse' in its string."""
    f = ReverseBuilder().audio_filter()
    assert "areverse" in str(f), f"expected 'areverse' in audio filter, got: {f}"


def test_reverse_builder_video_filter_not_areverse() -> None:
    """ReverseBuilder().video_filter() produces 'reverse', not 'areverse'."""
    f = str(ReverseBuilder().video_filter())
    assert not f.startswith("areverse"), f"video_filter must not be areverse, got: {f}"


def test_reverse_builder_repr() -> None:
    """ReverseBuilder.__repr__ returns 'ReverseBuilder()'."""
    assert repr(ReverseBuilder()) == "ReverseBuilder()"


# ---------------------------------------------------------------------------
# EffectDefinition tests
# ---------------------------------------------------------------------------


def test_reverse_registered_in_default_registry() -> None:
    """REVERSE is registered under 'reverse' in the default registry (BL-444-AC-1)."""
    from stoat_ferret.effects.definitions import create_default_registry

    registry = create_default_registry()
    assert registry.get("reverse") is not None, "reverse effect must be registered"


def test_reverse_build_fn_returns_reverse_filter() -> None:
    """REVERSE.build_fn returns a filter string containing 'reverse' (BL-444-AC-1)."""
    from stoat_ferret.effects.definitions import REVERSE

    result = REVERSE.build_fn({})
    assert "reverse" in result, f"Expected 'reverse' in filter string: {result}"


def test_reverse_effect_has_no_required_parameters() -> None:
    """REVERSE parameter schema has no required parameters."""
    from stoat_ferret.effects.definitions import REVERSE

    required = REVERSE.parameter_schema.get("required", [])
    assert required == [], f"Expected no required parameters, got: {required}"


def test_reverse_effect_additionalproperties_false() -> None:
    """REVERSE parameter schema rejects unknown parameters."""
    from stoat_ferret.effects.definitions import REVERSE

    assert REVERSE.parameter_schema.get("additionalProperties") is False


def test_reverse_preview_fn_contains_reverse() -> None:
    """REVERSE.preview_fn returns a filter string containing 'reverse'."""
    from stoat_ferret.effects.definitions import REVERSE

    result = REVERSE.preview_fn()
    assert "reverse" in result, f"Expected 'reverse' in preview filter string: {result}"


# ---------------------------------------------------------------------------
# Settings tests — buffer limit default and validation (BL-444-AC-3)
# ---------------------------------------------------------------------------


def test_settings_reverse_max_duration_s_default() -> None:
    """reverse_max_duration_s defaults to 30.0 seconds."""
    from stoat_ferret.api.settings import Settings

    s = Settings()
    assert s.reverse_max_duration_s == 30.0


def test_settings_reverse_max_duration_s_invalid_zero() -> None:
    """reverse_max_duration_s=0.0 raises ValidationError at instantiation."""
    from pydantic import ValidationError

    from stoat_ferret.api.settings import Settings

    with pytest.raises(ValidationError):
        Settings(reverse_max_duration_s=0.0)


def test_settings_reverse_max_duration_s_invalid_negative() -> None:
    """reverse_max_duration_s=-1.0 raises ValidationError at instantiation."""
    from pydantic import ValidationError

    from stoat_ferret.api.settings import Settings

    with pytest.raises(ValidationError):
        Settings(reverse_max_duration_s=-1.0)


# ---------------------------------------------------------------------------
# API tests — buffer-limit guard (BL-444-AC-3)
# ---------------------------------------------------------------------------

_PROJECT_ID = "proj-reverse-limit"
_CLIP_SHORT = "clip-reverse-short"  # 15s at 30fps (within 30s default)
_CLIP_LONG = "clip-reverse-long"  # 31s at 30fps (exceeds 30s default)
_FPS = 30


def _make_client_with_clips() -> tuple[TestClient, str, str]:
    """Create a TestClient with a seeded project and two clips.

    Returns (client, short_clip_id, long_clip_id).
    """
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
        name="Reverse Limit Test",
        output_width=1920,
        output_height=1080,
        output_fps=_FPS,
        created_at=now,
        updated_at=now,
    )
    video = make_test_video()
    short_clip = Clip(
        id=_CLIP_SHORT,
        project_id=_PROJECT_ID,
        source_video_id=video.id,
        in_point=0,
        out_point=450,  # 15s at 30fps — within the 30s default limit
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    long_clip = Clip(
        id=_CLIP_LONG,
        project_id=_PROJECT_ID,
        source_video_id=video.id,
        in_point=0,
        out_point=930,  # 31s at 30fps — exceeds the 30s default limit
        timeline_position=450,
        created_at=now,
        updated_at=now,
    )

    loop = asyncio.new_event_loop()
    loop.run_until_complete(project_repo.add(project))
    loop.run_until_complete(video_repo.add(video))
    loop.run_until_complete(clip_repo.add(short_clip))
    loop.run_until_complete(clip_repo.add(long_clip))
    loop.close()

    app = create_app(
        project_repository=project_repo,
        clip_repository=clip_repo,
        video_repository=video_repo,
    )
    return TestClient(app), _CLIP_SHORT, _CLIP_LONG


@pytest.mark.api
def test_apply_reverse_within_limit_returns_201() -> None:
    """Applying reverse to a clip within the duration limit returns 201 (BL-444-AC-2)."""
    client, short_clip, _ = _make_client_with_clips()
    with client, patch("stoat_ferret.api.settings.get_settings") as mock_gs:
        mock_gs.return_value = MagicMock(reverse_max_duration_s=30.0)
        response = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{short_clip}/effects",
            json={"effect_type": "reverse", "parameters": {}},
        )
    assert response.status_code == 201, (
        f"Expected 201 for 15s clip with 30s limit, got {response.status_code}: {response.json()}"
    )


@pytest.mark.api
def test_apply_reverse_exceeding_limit_returns_422() -> None:
    """Applying reverse to a clip exceeding the duration limit returns HTTP 422 (BL-444-AC-3)."""
    client, _, long_clip = _make_client_with_clips()
    with client, patch("stoat_ferret.api.settings.get_settings") as mock_gs:
        mock_gs.return_value = MagicMock(reverse_max_duration_s=30.0)
        response = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{long_clip}/effects",
            json={"effect_type": "reverse", "parameters": {}},
        )
    assert response.status_code == 422, (
        f"Expected 422 for 31s clip with 30s limit, got {response.status_code}: {response.json()}"
    )
    detail = response.json()["detail"]
    assert detail.get("error") == "clip_too_long", f"Expected clip_too_long error key: {detail}"
    assert "max_s" in detail, f"Expected max_s in response detail: {detail}"
    assert "clip_s" in detail, f"Expected clip_s in response detail: {detail}"


@pytest.mark.api
def test_apply_reverse_custom_limit_enforced_from_settings() -> None:
    """Buffer limit is read from settings — a 5s cap rejects a 15s clip (BL-444-AC-3)."""
    client, short_clip, _ = _make_client_with_clips()
    with client, patch("stoat_ferret.api.settings.get_settings") as mock_gs:
        mock_gs.return_value = MagicMock(reverse_max_duration_s=5.0)
        response = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{short_clip}/effects",
            json={"effect_type": "reverse", "parameters": {}},
        )
    assert response.status_code == 422, (
        f"Expected 422 when limit is 5s and clip is 15s, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# FFmpeg-gated contract tests (require STOAT_TEST_FFMPEG=1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg required; set STOAT_TEST_FFMPEG=1",
)
def test_reverse_video_filter_produces_valid_output(tmp_path: str) -> None:
    """ReverseBuilder().video_filter() applied via FFmpeg reverses a test clip (BL-444-AC-4)."""
    import subprocess
    from pathlib import Path

    tmp = Path(str(tmp_path))
    source = tmp / "source.mp4"
    reversed_out = tmp / "reversed.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=3:size=160x90:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=3",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-t",
            "3",
            str(source),
        ],
        check=True,
        capture_output=True,
    )

    video_f = str(ReverseBuilder().video_filter())
    audio_f = str(ReverseBuilder().audio_filter())
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vf",
            video_f,
            "-af",
            audio_f,
            str(reversed_out),
        ],
        check=True,
        capture_output=True,
    )

    assert reversed_out.exists(), "reversed output file must exist after render"
    assert reversed_out.stat().st_size > 0, "reversed output must be non-empty"
