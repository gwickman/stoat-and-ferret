# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for volume automation eval=frame filter string (BL-479)."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.effects.definitions import create_default_registry
from stoat_ferret.effects.registry import EffectRegistry
from tests.factories import make_test_video


@pytest.fixture()
def registry() -> EffectRegistry:
    """Fully-populated EffectRegistry for automation dispatch tests."""
    return create_default_registry()


@pytest.mark.contract
def test_build_automation_filter_string_contains_eval_frame() -> None:
    """build_automation_filter_string returns volume filter with :eval=frame (BL-479-AC-2)."""
    registry = create_default_registry()
    result = registry.build_automation_filter_string("volume", "0.1+0.08*t")
    assert "eval=frame" in result, f"Expected 'eval=frame' in filter string: {result}"
    assert "volume=" in result, f"Expected 'volume=' in filter string: {result}"


@pytest.mark.contract
def test_build_automation_filter_string_embeds_expression() -> None:
    """build_automation_filter_string wraps the compiled expression in single quotes."""
    registry = create_default_registry()
    expr = "0.1+0.08*t"
    result = registry.build_automation_filter_string("volume", expr)
    assert f"'{expr}'" in result, f"Expected expression quoted in: {result}"


@pytest.mark.contract
def test_build_automation_filter_string_unknown_type_raises() -> None:
    """build_automation_filter_string raises ValueError for non-automatable types."""
    registry = create_default_registry()
    with pytest.raises(ValueError, match="No automation filter string for effect_type"):
        registry.build_automation_filter_string("text_overlay", "some_expr")


@pytest.mark.contract
def test_scalar_volume_filter_has_no_eval_frame() -> None:
    """Scalar volume build_fn does NOT include eval=frame (BL-479-AC-3, static path unchanged)."""
    registry = create_default_registry()
    definition = registry.get("volume")
    assert definition is not None
    filter_str = definition.build_fn({"volume": 0.5})
    assert "eval=frame" not in filter_str, (
        f"eval=frame should not appear in scalar filter string: {filter_str}"
    )


def _make_client_with_clip() -> tuple[TestClient, str, str]:
    """Create a TestClient with a seeded project and clip. Returns (client, project_id, clip_id)."""
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    video_repo = AsyncInMemoryVideoRepository()

    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-vol-auto",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    video = make_test_video()
    clip = Clip(
        id="clip-vol-auto",
        project_id="proj-vol-auto",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )

    import asyncio

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
    return TestClient(app), "proj-vol-auto", "clip-vol-auto"


@pytest.mark.api
def test_apply_endpoint_automation_filter_contains_eval_frame() -> None:
    """apply endpoint with automation envelope stores filter_string with :eval=frame.

    BL-479-AC-2.
    """
    with _make_client_with_clip()[0] as client:
        response = client.post(
            "/api/v1/projects/proj-vol-auto/clips/clip-vol-auto/effects",
            json={
                "effect_type": "volume",
                "parameters": {
                    "volume": {
                        "default": 0.1,
                        "keyframes": [
                            {"t": 0.0, "value": 0.1, "curve": "linear"},
                            {"t": 5.0, "value": 0.9, "curve": "linear"},
                        ],
                    }
                },
            },
        )
    assert response.status_code == 201, f"Expected 201: {response.json()}"
    data = response.json()
    assert "eval=frame" in data["filter_string"], (
        f"Expected 'eval=frame' in apply filter_string: {data['filter_string']}"
    )


def test_build_automation_filter_string_unknown_raises(registry: EffectRegistry) -> None:
    """ValueError raised for unregistered or non-automatable effect types."""
    with pytest.raises(ValueError, match="No automation filter string"):
        registry.build_automation_filter_string("nonexistent_effect", "expr")


def test_build_automation_filter_string_volume_unchanged(registry: EffectRegistry) -> None:
    """Volume template path is backward-compatible with the old hardcoded result."""
    result = registry.build_automation_filter_string("volume", "if(lt(t,1),0.5,1.0)")
    assert result.startswith("volume=")
    assert "eval=frame" in result


def test_build_automation_filter_string_blur_radius(registry: EffectRegistry) -> None:
    """build_automation_filter_string for 'blur' produces gblur sigma eval=frame (BL-451-AC-3)."""
    result = registry.build_automation_filter_string("blur", "1+0.5*t")
    assert "eval=frame" in result, f"Expected eval=frame in blur filter: {result}"
    assert "gblur" in result, f"Expected gblur in blur filter: {result}"
    assert "1+0.5*t" in result, f"Expected expression in blur filter: {result}"


def test_build_automation_filter_string_opacity(registry: EffectRegistry) -> None:
    """build_automation_filter_string for 'opacity' → geq with uppercase-T (BL-502)."""
    result = registry.build_automation_filter_string("opacity", "0.5+0.5*sin(t)")
    assert "geq=" in result, f"Expected geq= in opacity filter: {result}"
    assert "colorchannelmixer" not in result, f"colorchannelmixer must be absent: {result}"
    # lowercase t converted to uppercase T for geq time variable
    assert "sin(T)" in result, f"Expected sin(T) (uppercase) in opacity filter: {result}"


def test_build_automation_filter_string_opacity_uppercase_t(registry: EffectRegistry) -> None:
    """Word-boundary re.sub converts standalone t → T, not t inside function names (BL-502)."""
    result = registry.build_automation_filter_string("opacity", "lt(t,1.0)")
    # commas in expressions are escaped; standalone t converts to T, lt stays as lt
    assert r"lt(T\,1.0)" in result, f"Expected lt(T\\,1.0) in result: {result}"
    assert r"lt(t\,1.0)" not in result, f"Lowercase lt(t\\,1.0) must not appear: {result}"


def test_build_automation_filter_string_scale(registry: EffectRegistry) -> None:
    """build_automation_filter_string for 'scale' produces scale trunc eval=frame (BL-455-AC-2)."""
    result = registry.build_automation_filter_string("scale", "1+0.1*t")
    assert "eval=frame" in result, f"Expected eval=frame in scale filter: {result}"
    assert "scale=" in result, f"Expected scale= in scale filter: {result}"
    assert "1+0.1*t" in result, f"Expected expression in scale filter: {result}"


@pytest.mark.api
def test_update_endpoint_automation_filter_contains_eval_frame() -> None:
    """update endpoint with automation envelope stores filter_string with :eval=frame.

    BL-479-AC-2.
    """
    client_ctx, proj_id, clip_id = _make_client_with_clip()
    with client_ctx as client:
        apply_resp = client.post(
            f"/api/v1/projects/{proj_id}/clips/{clip_id}/effects",
            json={"effect_type": "volume", "parameters": {"volume": 0.5}},
        )
        assert apply_resp.status_code == 201

        update_resp = client.patch(
            f"/api/v1/projects/{proj_id}/clips/{clip_id}/effects/0",
            json={
                "parameters": {
                    "volume": {
                        "default": 0.1,
                        "keyframes": [
                            {"t": 0.0, "value": 0.1, "curve": "linear"},
                            {"t": 5.0, "value": 0.9, "curve": "linear"},
                        ],
                    }
                }
            },
        )
    assert update_resp.status_code == 200, f"Expected 200: {update_resp.json()}"
    data = update_resp.json()
    assert "eval=frame" in data["filter_string"], (
        f"Expected 'eval=frame' in update filter_string: {data['filter_string']}"
    )


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="Requires STOAT_TEST_FFMPEG=1",
)
def test_volume_automation_level_follows_curve(tmp_path: Path) -> None:
    """AC-1: quiet-start/loud-end volume envelope yields end level >= start + 5 dB (BL-687-AC-1)."""
    input_path = tmp_path / "sine.wav"
    output_path = tmp_path / "automated.wav"

    # Generate 6-second constant sine wave at full scale.
    # lavfi sine emits at 0.125 amplitude; volume=8 brings it to 1.0.
    gen = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=6",
            "-af",
            "volume=8",
            "-c:a",
            "pcm_f32le",
            "-ar",
            "44100",
            "-y",
            str(input_path),
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert gen.returncode == 0, f"Sine fixture failed: {gen.stderr.decode()}"

    # Build volume automation: ramps 0.1 -> 1.0 over 5 s, then holds 1.0.
    # At t=0 volume=0.1 (~-20 dBFS), at t=5 volume=1.0 (~0 dBFS): delta ~20 dB >> 5 dB threshold.
    registry = create_default_registry()
    filter_str = registry.build_automation_filter_string("volume", "if(lt(t,5),0.1+0.18*t,1.0)")

    render = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(input_path),
            "-af",
            filter_str,
            "-c:a",
            "pcm_f32le",
            "-ar",
            "44100",
            "-y",
            str(output_path),
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert render.returncode == 0, f"Volume automation render failed: {render.stderr.decode()}"
    assert output_path.stat().st_size > 0, "Output file is empty"

    def _mean_db(path: Path, offset: float, duration: float = 0.5) -> float:
        """Return mean volume (dBFS) of a window via volumedetect."""
        probe = subprocess.run(
            [
                "ffmpeg",
                "-ss",
                str(offset),
                "-i",
                str(path),
                "-t",
                str(duration),
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
        for line in probe.stderr.decode().splitlines():
            if "mean_volume" in line:
                parts = line.split("mean_volume:")
                if len(parts) > 1:
                    return float(parts[1].strip().split()[0])
        pytest.skip(f"Could not parse mean_volume: {probe.stderr.decode()[:500]}")

    start_db = _mean_db(output_path, offset=0.1)
    end_db = _mean_db(output_path, offset=5.0)

    assert end_db >= start_db + 5.0, (
        f"End level {end_db:.1f} dBFS must be at least 5 dB above "
        f"start {start_db:.1f} dBFS (delta: {end_db - start_db:.1f} dB)"
    )
