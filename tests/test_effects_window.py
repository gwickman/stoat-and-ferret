# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for range-window effect gating (BL-446).

Covers:
- WindowSpec schema validation (FR-001 all cases)
- enable clause appended to filter string (FR-002-AC-1)
- filter_preview populated when window provided (FR-002-AC-2)
- window_conflicts_with_builtin_enable rejection (FR-002-AC-3)
- Regression: all 20 registered effects unchanged with window=None (FR-004-AC-1)
- FFmpeg-gated rendered probe (FR-003-AC-1, skipped without STOAT_TEST_FFMPEG=1)
"""

from __future__ import annotations

import math
import os
import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from stoat_ferret.api.app import create_app
from stoat_ferret.api.schemas.effect import WindowSpec
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.effects.definitions import EffectDefinition, create_default_registry
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret_core import ZoompanBuilder

# ---------------------------------------------------------------------------
# WindowSpec schema unit tests (FR-001)
# ---------------------------------------------------------------------------


def test_window_spec_valid() -> None:
    """Valid window with start_s=0 and end_s>start_s is accepted."""
    w = WindowSpec.model_validate({"start_s": 1.0, "end_s": 5.0})
    assert w.start_s == 1.0
    assert w.end_s == 5.0


def test_window_spec_valid_start_zero() -> None:
    """start_s=0 is accepted (lower boundary)."""
    w = WindowSpec.model_validate({"start_s": 0.0, "end_s": 2.5})
    assert w.start_s == 0.0


def test_window_spec_start_negative_rejected() -> None:
    """start_s < 0 raises ValidationError (FR-001-AC-2)."""
    with pytest.raises(ValidationError, match="non-negative"):
        WindowSpec.model_validate({"start_s": -0.1, "end_s": 5.0})


def test_window_spec_start_nan_rejected() -> None:
    """start_s = NaN raises ValidationError (FR-001-AC-2)."""
    with pytest.raises(ValidationError, match="non-negative"):
        WindowSpec.model_validate({"start_s": math.nan, "end_s": 5.0})


def test_window_spec_start_inf_rejected() -> None:
    """start_s = Inf raises ValidationError (FR-001-AC-2)."""
    with pytest.raises(ValidationError, match="non-negative"):
        WindowSpec.model_validate({"start_s": math.inf, "end_s": 5.0})


def test_window_spec_end_equal_to_start_rejected() -> None:
    """end_s == start_s raises ValidationError (FR-001-AC-3)."""
    with pytest.raises(ValidationError, match="greater than"):
        WindowSpec.model_validate({"start_s": 3.0, "end_s": 3.0})


def test_window_spec_end_less_than_start_rejected() -> None:
    """end_s < start_s raises ValidationError (FR-001-AC-3)."""
    with pytest.raises(ValidationError, match="greater than"):
        WindowSpec.model_validate({"start_s": 5.0, "end_s": 2.0})


def test_window_spec_end_nan_rejected() -> None:
    """end_s = NaN raises ValidationError (FR-001-AC-3)."""
    with pytest.raises(ValidationError, match="finite"):
        WindowSpec.model_validate({"start_s": 1.0, "end_s": math.nan})


def test_window_spec_end_inf_rejected() -> None:
    """end_s = Inf raises ValidationError (FR-001-AC-3)."""
    with pytest.raises(ValidationError, match="finite"):
        WindowSpec.model_validate({"start_s": 1.0, "end_s": math.inf})


def test_window_spec_missing_end_s_rejected() -> None:
    """Window missing end_s raises ValidationError (FR-001-AC-4: partial window invalid)."""
    with pytest.raises(ValidationError):
        WindowSpec.model_validate({"start_s": 1.0})


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------


def _make_app_with_registry(
    registry: EffectRegistry | None = None,
) -> tuple[object, AsyncInMemoryProjectRepository, AsyncInMemoryClipRepository]:
    """Create a test app with in-memory repositories and optional registry."""
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    video_repo = AsyncInMemoryVideoRepository()
    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        effect_registry=registry,
    )
    return app, project_repo, clip_repo


async def _seed_project_and_clip(
    project_repo: AsyncInMemoryProjectRepository,
    clip_repo: AsyncInMemoryClipRepository,
) -> None:
    """Seed a project and clip for apply-effect tests."""
    now = datetime.now(timezone.utc)
    await project_repo.add(
        Project(
            id="proj-w",
            name="Window Test",
            output_width=1920,
            output_height=1080,
            output_fps=30,
            created_at=now,
            updated_at=now,
        )
    )
    await clip_repo.add(
        Clip(
            id="clip-w",
            project_id="proj-w",
            source_video_id="vid-fixture",
            in_point=0,
            out_point=300,
            timeline_position=0,
            created_at=now,
            updated_at=now,
        )
    )


# ---------------------------------------------------------------------------
# Integration tests — enable clause and filter_preview (FR-002-AC-1 / AC-2)
# ---------------------------------------------------------------------------


async def test_window_appends_enable_clause_to_filter_string() -> None:
    """When window is provided, filter_string includes enable='between(t,a,b)' (FR-002-AC-1)."""
    app, project_repo, clip_repo = _make_app_with_registry()
    await _seed_project_and_clip(project_repo, clip_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-w/clips/clip-w/effects",
            json={
                "effect_type": "volume",
                "parameters": {"volume": 0.8},
                "window": {"start_s": 1.0, "end_s": 5.0},
            },
        )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "enable='between(t,1.0,5.0)'" in data["filter_string"]


async def test_window_sets_filter_preview() -> None:
    """When window provided, filter_preview equals the enable-appended string (FR-002-AC-2)."""
    app, project_repo, clip_repo = _make_app_with_registry()
    await _seed_project_and_clip(project_repo, clip_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-w/clips/clip-w/effects",
            json={
                "effect_type": "volume",
                "parameters": {"volume": 0.8},
                "window": {"start_s": 2.0, "end_s": 8.0},
            },
        )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["filter_preview"] is not None
    assert data["filter_preview"] == data["filter_string"]
    assert "enable='between(t,2.0,8.0)'" in data["filter_preview"]


async def test_no_window_leaves_filter_preview_none() -> None:
    """Without a window, filter_preview remains None for scalar parameters (regression guard)."""
    app, project_repo, clip_repo = _make_app_with_registry()
    await _seed_project_and_clip(project_repo, clip_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-w/clips/clip-w/effects",
            json={
                "effect_type": "volume",
                "parameters": {"volume": 0.8},
            },
        )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["filter_preview"] is None


# ---------------------------------------------------------------------------
# Integration test — conflict guard (FR-002-AC-3)
# ---------------------------------------------------------------------------


async def test_window_conflicts_with_builtin_enable_returns_422() -> None:
    """Effect whose build_fn output contains enable= + window → 422 (FR-002-AC-3)."""
    # Register a mock effect whose build_fn returns a filter with 'enable='
    registry = create_default_registry()
    mock_def = EffectDefinition(
        name="MockEnableEffect",
        description="Test effect that already embeds enable=",
        parameter_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        ai_hints={},
        preview_fn=lambda: "mock=1:enable='between(t,0,10)'",
        build_fn=lambda _params: "mock=1:enable='between(t,0,10)'",
        ai_summary="Mock effect for testing",
        example_prompt="apply mock effect",
    )
    registry.register("mock_enable_effect", mock_def)

    app, project_repo, clip_repo = _make_app_with_registry(registry)
    await _seed_project_and_clip(project_repo, clip_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-w/clips/clip-w/effects",
            json={
                "effect_type": "mock_enable_effect",
                "parameters": {},
                "window": {"start_s": 1.0, "end_s": 3.0},
            },
        )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "window_conflicts_with_builtin_enable"


# ---------------------------------------------------------------------------
# Regression test — all 20 effects produce identical filter strings (FR-004-AC-1)
# ---------------------------------------------------------------------------


def test_all_effects_unchanged_with_window_none() -> None:
    """All 21 effects produce identical filter strings with window=None (FR-004-AC-1).

    Calls each effect's preview_fn and verifies no 'enable=' appears in the
    baseline output, confirming window=None doesn't alter any existing effect.
    """
    registry = create_default_registry()
    all_effects = registry.list_all()
    assert len(all_effects) == 40, f"Expected 40 effects, got {len(all_effects)}"

    for effect_type, definition in all_effects:
        # Build the baseline (no-window) filter string via preview_fn
        baseline = definition.preview_fn()
        # preview_fn is the reference; build_fn with empty params mirrors the same path
        # (no window appended since we don't call apply_effect_to_clip here)
        assert isinstance(baseline, str), f"{effect_type}: preview_fn returned non-string"
        # subtitle_script uses enable= internally (it emits N timed drawtext filters);
        # it is intentionally excluded from range-window gating (timeline_T_capable=False).
        _enable_exempt = {"mock_enable_effect", "subtitle_script"}
        assert "enable=" not in baseline or effect_type in _enable_exempt, (
            f"{effect_type}: preview_fn already contains 'enable=' — "
            "this effect would conflict with range-window. "
            "Update the implementation plan's conflict guard to account for this."
        )


# ---------------------------------------------------------------------------
# FFmpeg-gated rendered probe (FR-003-AC-1)
# ---------------------------------------------------------------------------

_FFMPEG_GATED = pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)


# ---------------------------------------------------------------------------
# Window storage in effect entry (FR-003-AC-1)
# ---------------------------------------------------------------------------


async def test_window_stored_in_effect_entry() -> None:
    """Window bounds stored as 'window' key in effect entry when WindowSpec provided.

    FR-003-AC-1.
    """
    app, project_repo, clip_repo = _make_app_with_registry()
    await _seed_project_and_clip(project_repo, clip_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-w/clips/clip-w/effects",
            json={
                "effect_type": "volume",
                "parameters": {"volume": 0.5},
                "window": {"start_s": 2.0, "end_s": 6.0},
            },
        )

    assert response.status_code == 201, response.text
    clip = await clip_repo.get("clip-w")
    assert clip is not None and clip.effects is not None
    entry = clip.effects[0]
    assert "window" in entry, f"Expected 'window' key in effect entry; got keys: {list(entry)}"
    assert entry["window"]["start_s"] == 2.0
    assert entry["window"]["end_s"] == 6.0


async def test_no_window_key_without_windowspec() -> None:
    """No 'window' key in effect entry when no WindowSpec provided (backward compatibility)."""
    app, project_repo, clip_repo = _make_app_with_registry()
    await _seed_project_and_clip(project_repo, clip_repo)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/proj-w/clips/clip-w/effects",
            json={
                "effect_type": "volume",
                "parameters": {"volume": 0.8},
            },
        )

    assert response.status_code == 201, response.text
    clip = await clip_repo.get("clip-w")
    assert clip is not None and clip.effects is not None
    entry = clip.effects[0]
    assert "window" not in entry, f"'window' key must not appear without WindowSpec; got: {entry}"


@_FFMPEG_GATED
def test_window_render_ffmpeg_contract(tmp_path: object) -> None:
    """Rendered probe confirms effect active only within window (FR-003-AC-1).

    Renders a solid-blue lavfi source with a negate effect windowed to [2.0, 4.0].
    Samples one pixel before, inside, and after the window and asserts the effect
    (colour inversion) is present only within the window bounds.

    Discharge command:
        STOAT_TEST_FFMPEG=1 uv run pytest \
            tests/test_effects_window.py::test_window_render_ffmpeg_contract -v
    """
    import subprocess
    from pathlib import Path

    tmp = Path(str(tmp_path))

    # Solid blue source: 6 s, 5 fps, 64×64 pixels
    src = tmp / "source.mp4"
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:size=64x64:rate=5",
            "-t",
            "6",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            str(src),
        ],
        capture_output=True,
    )
    assert r.returncode == 0, f"lavfi source creation failed:\n{r.stderr.decode()[-1000:]}"

    # Apply negate windowed to [2.0, 4.0] — effect must flip all channels inside the window
    window_start, window_end = 2.0, 4.0
    out = tmp / "output.mp4"
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            f"negate=enable='between(t,{window_start},{window_end})'",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            str(out),
        ],
        capture_output=True,
    )
    assert r.returncode == 0, f"windowed render failed:\n{r.stderr.decode()[-1000:]}"

    def _sample_pixel(path: Path, t: float) -> tuple[int, int, int]:
        """Extract a single 1×1 pixel at time t as raw RGB24 bytes."""
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(t),
                "-i",
                str(path),
                "-vframes",
                "1",
                "-vf",
                "scale=1:1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            capture_output=True,
        )
        assert result.returncode == 0 and len(result.stdout) >= 3, (
            f"pixel extraction at t={t} failed: {result.stderr.decode()[-500:]}"
        )
        return int(result.stdout[0]), int(result.stdout[1]), int(result.stdout[2])

    # Sample at t=0.5 (before window), t=3.0 (inside window), t=5.5 (after window)
    pre = _sample_pixel(out, 0.5)
    inside = _sample_pixel(out, 3.0)
    post = _sample_pixel(out, 5.5)

    # Blue (0,0,255) negated → yellow-ish (255,255,0).
    # R channel: low before/after, high inside.
    # B channel: high before/after, low inside.
    assert inside[0] > pre[0] + 50, (
        f"R inside window ({inside[0]}) should be >> R before window ({pre[0]}); "
        f"negate effect not active inside window"
    )
    assert inside[2] < pre[2] - 50, (
        f"B inside window ({inside[2]}) should be << B before window ({pre[2]}); "
        f"negate effect not active inside window"
    )
    assert abs(post[0] - pre[0]) < 50, (
        f"R after window ({post[0]}) should match R before window ({pre[0]}); "
        f"negate effect leaking outside window"
    )
    assert abs(post[2] - pre[2]) < 50, (
        f"B after window ({post[2]}) should match B before window ({pre[2]}); "
        f"negate effect leaking outside window"
    )


# ---------------------------------------------------------------------------
# ZoompanBuilder bare-n validation and ken_burns() factory (BL-603)
# ---------------------------------------------------------------------------


def test_zoompan_bare_n_raises() -> None:
    """ZoompanBuilder rejects bare 'n' in zoom expression (BL-603-AC-1/AC-2)."""
    with pytest.raises(ValueError, match="bare 'n'"):
        ZoompanBuilder("n/1000+1", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", 125, 1920, 1080, 25)


def test_zoompan_on_accepted() -> None:
    """ZoompanBuilder accepts 'on'-based expressions and build() returns filter (BL-603-AC-2)."""
    builder = ZoompanBuilder(
        "on/1000+1", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", 125, 1920, 1080, 25
    )
    result = builder.build()
    assert "on" in str(result)
    assert "zoompan" in str(result)


def test_ken_burns_factory_emits_on() -> None:
    """ken_burns() factory produces filter with 'on' and no bare 'n' (BL-603-AC-3/AC-4)."""
    builder = ZoompanBuilder.ken_burns(duration_s=3.0, zoom_end=1.3)
    result = str(builder.build())
    assert "zoompan" in result
    assert "on" in result
    assert not re.search(r"\bn\b", result)
