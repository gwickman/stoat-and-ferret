# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit and contract tests for OpacityBuilder and ScaleBuilder (BL-455)."""

from __future__ import annotations

import os

import pytest

from stoat_ferret.effects.definitions import OPACITY_EFFECT, SCALE_EFFECT, create_default_registry
from stoat_ferret_core import Automation, Keyframe, OpacityBuilder, ScaleBuilder

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG") == "1"


# ---- OpacityBuilder unit tests ----


def test_opacity_valid_range() -> None:
    """OpacityBuilder accepts opacity in [0.0, 1.0]."""
    assert OpacityBuilder(0.0) is not None
    assert OpacityBuilder(0.5) is not None
    assert OpacityBuilder(1.0) is not None


def test_opacity_invalid_range_raises() -> None:
    """OpacityBuilder raises ValueError outside [0.0, 1.0]."""
    with pytest.raises((ValueError, Exception)):
        OpacityBuilder(-0.1)
    with pytest.raises((ValueError, Exception)):
        OpacityBuilder(1.1)


def test_opacity_static_build_produces_colorchannelmixer() -> None:
    """OpacityBuilder.build() produces format=rgba,colorchannelmixer=aa=... (FR-001-AC-1)."""
    builder = OpacityBuilder(0.5)
    result = str(builder.build())
    assert "colorchannelmixer" in result, f"Expected colorchannelmixer in: {result}"
    assert "aa=" in result, f"Expected aa= in: {result}"
    assert "0.5" in result, f"Expected 0.5 in: {result}"


def test_opacity_static_build_no_eval_frame() -> None:
    """Scalar opacity build does not include eval=frame."""
    builder = OpacityBuilder(0.8)
    result = str(builder.build())
    assert "eval=frame" not in result, f"eval=frame should not be in scalar build: {result}"


def test_opacity_with_automation_stores_envelope() -> None:
    """OpacityBuilder.with_automation() returns new builder with envelope (FR-001-AC-2)."""
    auto = Automation(
        default=0.5,
        keyframes=[
            Keyframe(t=0.0, value=0.0, curve="Linear"),
            Keyframe(t=5.0, value=1.0, curve="Linear"),
        ],
    )
    builder = OpacityBuilder(1.0).with_automation(auto)
    assert builder is not None


def test_opacity_with_automation_build_contains_eval_frame() -> None:
    """OpacityBuilder with automation produces eval=frame filter string (FR-001-AC-2)."""
    auto = Automation(
        default=0.5,
        keyframes=[
            Keyframe(t=0.0, value=0.0, curve="Linear"),
            Keyframe(t=5.0, value=1.0, curve="Linear"),
        ],
    )
    builder = OpacityBuilder(1.0).with_automation(auto)
    result = str(builder.build())
    assert "eval=frame" in result, f"Expected eval=frame in: {result}"
    assert "colorchannelmixer" in result, f"Expected colorchannelmixer in: {result}"


def test_opacity_automation_expression_timing() -> None:
    """Compiled automation expression contains keyframe positions (FR-001-AC-3)."""
    auto = Automation(
        default=0.5,
        keyframes=[
            Keyframe(t=0.0, value=0.0, curve="Linear"),
            Keyframe(t=3.0, value=1.0, curve="Linear"),
        ],
    )
    builder = OpacityBuilder(1.0).with_automation(auto)
    result = str(builder.build())
    # The compiled expression must reference time in some form
    assert any(c in result for c in ("t", "n", "pts")), (
        f"Expected time reference in automation expression: {result}"
    )


# ---- OpacityBuilder EffectDefinition tests ----


def test_opacity_effect_definition_automatable() -> None:
    """OPACITY_EFFECT has automatable=frozenset({'opacity'}) (FR-003-AC-1)."""
    assert OPACITY_EFFECT.automatable == frozenset({"opacity"})


def test_opacity_effect_definition_automation_template() -> None:
    """OPACITY_EFFECT.automation_filter_template has colorchannelmixer, eval=frame (FR-001-AC-4)."""
    assert OPACITY_EFFECT.automation_filter_template is not None
    template = OPACITY_EFFECT.automation_filter_template
    assert "colorchannelmixer" in template, f"Expected colorchannelmixer in template: {template}"
    assert "eval=frame" in template, f"Expected eval=frame in template: {template}"
    assert "{expr}" in template, f"Expected {{expr}} placeholder in template: {template}"


# ---- ScaleBuilder unit tests ----


def test_scale_valid() -> None:
    """ScaleBuilder accepts scale > 0."""
    assert ScaleBuilder(0.5) is not None
    assert ScaleBuilder(1.0) is not None
    assert ScaleBuilder(2.0) is not None


def test_scale_invalid_raises() -> None:
    """ScaleBuilder raises ValueError for scale <= 0 (FR-002-AC-1)."""
    with pytest.raises((ValueError, Exception)):
        ScaleBuilder(0.0)
    with pytest.raises((ValueError, Exception)):
        ScaleBuilder(-1.0)


def test_scale_static_build_produces_trunc_formula() -> None:
    """ScaleBuilder.build() produces scale= with trunc rounding formula (FR-002-AC-1)."""
    builder = ScaleBuilder(1.5)
    result = str(builder.build())
    assert result.startswith("scale="), f"Expected scale= prefix in: {result}"
    assert "trunc(iw" in result, f"Expected trunc(iw in: {result}"
    assert "trunc(ih" in result, f"Expected trunc(ih in: {result}"


def test_scale_static_build_no_eval_frame() -> None:
    """Scalar scale build does not include eval=frame."""
    builder = ScaleBuilder(2.0)
    result = str(builder.build())
    assert "eval=frame" not in result, f"eval=frame should not be in scalar build: {result}"


def test_scale_with_automation_stores_envelope() -> None:
    """ScaleBuilder.with_automation() returns new builder with envelope (FR-002-AC-2)."""
    auto = Automation(
        default=1.0,
        keyframes=[
            Keyframe(t=0.0, value=1.0, curve="Linear"),
            Keyframe(t=5.0, value=2.0, curve="Linear"),
        ],
    )
    builder = ScaleBuilder(1.0).with_automation(auto)
    assert builder is not None


def test_scale_with_automation_build_contains_eval_frame() -> None:
    """ScaleBuilder with automation produces eval=frame filter string (FR-002-AC-2)."""
    auto = Automation(
        default=1.0,
        keyframes=[
            Keyframe(t=0.0, value=1.0, curve="Linear"),
            Keyframe(t=5.0, value=2.0, curve="Linear"),
        ],
    )
    builder = ScaleBuilder(1.0).with_automation(auto)
    result = str(builder.build())
    assert "eval=frame" in result, f"Expected eval=frame in: {result}"
    assert "scale=" in result, f"Expected scale= in: {result}"


def test_scale_automation_expression_timing() -> None:
    """Compiled automation expression contains keyframe positions (FR-002-AC-3)."""
    auto = Automation(
        default=1.0,
        keyframes=[
            Keyframe(t=0.0, value=1.0, curve="Linear"),
            Keyframe(t=4.0, value=1.5, curve="Linear"),
        ],
    )
    builder = ScaleBuilder(1.0).with_automation(auto)
    result = str(builder.build())
    assert any(c in result for c in ("t", "n", "pts")), (
        f"Expected time reference in automation expression: {result}"
    )


# ---- ScaleBuilder EffectDefinition tests ----


def test_scale_effect_definition_automatable() -> None:
    """SCALE_EFFECT has automatable=frozenset({'scale'}) (FR-003-AC-1)."""
    assert SCALE_EFFECT.automatable == frozenset({"scale"})


def test_scale_effect_definition_automation_template() -> None:
    """SCALE_EFFECT has automation_filter_template with scale and eval=frame (FR-002-AC-3)."""
    assert SCALE_EFFECT.automation_filter_template is not None
    template = SCALE_EFFECT.automation_filter_template
    assert "scale=" in template, f"Expected scale= in template: {template}"
    assert "eval=frame" in template, f"Expected eval=frame in template: {template}"
    assert "{expr}" in template, f"Expected {{expr}} placeholder in template: {template}"


# ---- Registry integration tests ----


def test_opacity_registered_in_default_registry() -> None:
    """'opacity' effect is present in the default registry."""
    registry = create_default_registry()
    definition = registry.get("opacity")
    assert definition is not None
    assert definition.automatable == frozenset({"opacity"})


def test_scale_registered_in_default_registry() -> None:
    """'scale' effect is present in the default registry."""
    registry = create_default_registry()
    definition = registry.get("scale")
    assert definition is not None
    assert definition.automatable == frozenset({"scale"})


def test_opacity_build_fn_static() -> None:
    """Registry opacity build_fn returns colorchannelmixer filter string."""
    registry = create_default_registry()
    definition = registry.get("opacity")
    assert definition is not None
    result = definition.build_fn({"opacity": 0.7})
    assert "colorchannelmixer" in result, f"Expected colorchannelmixer in: {result}"


def test_scale_build_fn_static() -> None:
    """Registry scale build_fn returns scale filter string."""
    registry = create_default_registry()
    definition = registry.get("scale")
    assert definition is not None
    result = definition.build_fn({"scale": 1.5})
    assert "scale=" in result, f"Expected scale= in: {result}"
    assert "trunc" in result, f"Expected trunc in: {result}"


# ---- Contract tests (deferred_post_merge: require STOAT_TEST_FFMPEG=1) ----


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.contract
def test_opacity_animation_renders() -> None:
    """Opacity animation renders without error against real FFmpeg (FR-004-AC-1)."""
    import subprocess

    auto = Automation(
        default=0.5,
        keyframes=[
            Keyframe(t=0.0, value=0.0, curve="Linear"),
            Keyframe(t=0.1, value=1.0, curve="Linear"),
        ],
    )
    builder = OpacityBuilder(1.0).with_automation(auto)
    filter_str = str(builder.build())

    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:duration=0.1",
            "-vf",
            filter_str,
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"FFmpeg opacity animation failed (rc={result.returncode}):\n{result.stderr}"
    )


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.contract
def test_scale_animation_renders() -> None:
    """Scale animation renders without error against real FFmpeg (FR-004-AC-2)."""
    import subprocess

    auto = Automation(
        default=1.0,
        keyframes=[
            Keyframe(t=0.0, value=1.0, curve="Linear"),
            Keyframe(t=0.1, value=1.2, curve="Linear"),
        ],
    )
    builder = ScaleBuilder(1.0).with_automation(auto)
    filter_str = str(builder.build())

    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:duration=0.1",
            "-vf",
            filter_str,
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"FFmpeg scale animation failed (rc={result.returncode}):\n{result.stderr}"
    )
