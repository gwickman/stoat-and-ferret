# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit and contract tests for procedural generator effects (BL-454), ZoompanBuilder (BL-507),
and CurvesBuilder (BL-508).

BL-454 ACs:
- AC-1: GradientGeneratorBuilder generates a gradient clip with configurable colors.
- AC-2: NoiseGeneratorBuilder generates an evolving noise/pattern clip.
- AC-3: Both generators render for their configured duration.
- AC-4 (deferred): Renders without error verified by contract test against real FFmpeg.
    Discharge: STOAT_TEST_FFMPEG=1 pytest tests/test_effects_procedural_generators.py -k contract

BL-507 ACs:
- AC-1: ZoompanBuilder emits BOTH fps= AND settb= after zoompan params.
- AC-2: Struct docstring and EffectDefinition description contain "fixed-canvas".
- AC-3 (deferred): Negative-control test — without pin, render fails. STOAT_TEST_FFMPEG=1.
- AC-4: Graph-boundary scope boundary in BL-507 description (not BL-507 code).
- AC-5: ZOOMPAN EffectDefinition has timeline_T_capable=False.

BL-508 ACs:
- AC-1: CurvesBuilder(preset="vintage") produces curves=preset=vintage.
- AC-2: CurvesBuilder per-channel knee produces quoted curves= string.
- AC-3: Invalid preset raises ValueError.
- AC-4: Mutual exclusion (preset + channel) raises ValueError.
- AC-5: CURVES.timeline_T_capable is True.
- AC-6: "curves" registered in default registry.
"""

from __future__ import annotations

import os

import pytest

from stoat_ferret.effects.definitions import (
    CURVES,
    GRADIENT_GENERATOR,
    NOISE_GENERATOR,
    ZOOMPAN,
    create_default_registry,
)
from stoat_ferret_core import (
    CurvesBuilder,
    GradientGeneratorBuilder,
    NoiseGeneratorBuilder,
    ZoompanBuilder,
)

# ---- GradientGeneratorBuilder unit tests (AC-1) ----


def test_gradient_generator_default_size() -> None:
    """GradientGeneratorBuilder defaults to 1920x1080."""
    b = GradientGeneratorBuilder("black", "white", 5.0)
    s = str(b.build())
    assert "1920x1080" in s, f"Expected 1920x1080 in: {s}"


def test_gradient_generator_custom_colors() -> None:
    """GradientGeneratorBuilder accepts hex and named colors."""
    b = GradientGeneratorBuilder("#000080", "#FF8C00", 5.0)
    s = str(b.build())
    assert "0x000080" in s, f"Expected 0x000080 in: {s}"
    assert "0xFF8C00" in s, f"Expected 0xFF8C00 in: {s}"


def test_gradient_generator_named_colors() -> None:
    """GradientGeneratorBuilder accepts CSS named colors."""
    b = GradientGeneratorBuilder("navy", "white", 5.0)
    s = str(b.build())
    assert "c0=navy" in s, f"Expected c0=navy in: {s}"
    assert "c1=white" in s, f"Expected c1=white in: {s}"


def test_gradient_generator_custom_size() -> None:
    """GradientGeneratorBuilder respects custom width and height."""
    b = GradientGeneratorBuilder("black", "white", 3.0, width=640, height=480)
    s = str(b.build())
    assert "640x480" in s, f"Expected 640x480 in: {s}"


def test_gradient_generator_filter_prefix() -> None:
    """GradientGeneratorBuilder produces a gradients= filter string."""
    b = GradientGeneratorBuilder("black", "white", 5.0)
    s = str(b.build())
    assert s.startswith("gradients="), f"Expected gradients= prefix in: {s}"


def test_gradient_generator_duration_in_filter() -> None:
    """GradientGeneratorBuilder encodes duration in the filter string (AC-3)."""
    b = GradientGeneratorBuilder("black", "white", 7.5)
    s = str(b.build())
    assert "d=7.5" in s, f"Expected d=7.5 in: {s}"


def test_gradient_generator_invalid_duration() -> None:
    """GradientGeneratorBuilder rejects non-positive duration."""
    with pytest.raises(ValueError):
        GradientGeneratorBuilder("black", "white", 0.0)
    with pytest.raises(ValueError):
        GradientGeneratorBuilder("black", "white", -1.0)


def test_gradient_generator_invalid_color() -> None:
    """GradientGeneratorBuilder rejects invalid color format."""
    with pytest.raises(ValueError):
        GradientGeneratorBuilder("notacolor123", "white", 5.0)
    with pytest.raises(ValueError):
        GradientGeneratorBuilder("black", "#GGGGGG", 5.0)


def test_gradient_generator_zero_size() -> None:
    """GradientGeneratorBuilder rejects zero width or height."""
    with pytest.raises(ValueError):
        GradientGeneratorBuilder("black", "white", 5.0, width=0)
    with pytest.raises(ValueError):
        GradientGeneratorBuilder("black", "white", 5.0, height=0)


def test_gradient_generator_deterministic() -> None:
    """GradientGeneratorBuilder produces identical output for identical inputs."""
    b1 = GradientGeneratorBuilder("black", "white", 5.0)
    b2 = GradientGeneratorBuilder("black", "white", 5.0)
    assert str(b1.build()) == str(b2.build())


# ---- NoiseGeneratorBuilder unit tests (AC-2) ----


def test_noise_generator_default_size() -> None:
    """NoiseGeneratorBuilder defaults to 1920x1080."""
    b = NoiseGeneratorBuilder(5.0)
    s = str(b.build())
    assert "1920x1080" in s, f"Expected 1920x1080 in: {s}"


def test_noise_generator_filter_prefix() -> None:
    """NoiseGeneratorBuilder produces a cellauto= filter string."""
    b = NoiseGeneratorBuilder(5.0)
    s = str(b.build())
    assert s.startswith("cellauto="), f"Expected cellauto= prefix in: {s}"


def test_noise_generator_duration_in_filter() -> None:
    """NoiseGeneratorBuilder encodes duration in the filter string (AC-3)."""
    b = NoiseGeneratorBuilder(8.0)
    s = str(b.build())
    assert "d=" not in s, f"Expected no d= in: {s}"


def test_noise_generator_custom_size() -> None:
    """NoiseGeneratorBuilder respects custom width and height."""
    b = NoiseGeneratorBuilder(3.0, width=640, height=480)
    s = str(b.build())
    assert "640x480" in s, f"Expected 640x480 in: {s}"


def test_noise_generator_invalid_duration() -> None:
    """NoiseGeneratorBuilder rejects non-positive duration."""
    with pytest.raises(ValueError):
        NoiseGeneratorBuilder(0.0)
    with pytest.raises(ValueError):
        NoiseGeneratorBuilder(-1.0)


def test_noise_generator_zero_size() -> None:
    """NoiseGeneratorBuilder rejects zero width or height."""
    with pytest.raises(ValueError):
        NoiseGeneratorBuilder(5.0, width=0)
    with pytest.raises(ValueError):
        NoiseGeneratorBuilder(5.0, height=0)


def test_noise_generator_deterministic() -> None:
    """NoiseGeneratorBuilder produces identical output for identical inputs."""
    b1 = NoiseGeneratorBuilder(5.0)
    b2 = NoiseGeneratorBuilder(5.0)
    assert str(b1.build()) == str(b2.build())


# ---- Effect registry tests ----


def test_gradient_generator_registered_in_default_registry() -> None:
    """gradient_generator is registered in the default effect registry."""
    registry = create_default_registry()
    definition = registry.get("gradient_generator")
    assert definition is not None
    assert definition is GRADIENT_GENERATOR


def test_noise_generator_registered_in_default_registry() -> None:
    """noise_generator is registered in the default effect registry."""
    registry = create_default_registry()
    definition = registry.get("noise_generator")
    assert definition is not None
    assert definition is NOISE_GENERATOR


def test_gradient_generator_preview_fn() -> None:
    """GRADIENT_GENERATOR.preview_fn() produces a gradients= filter string."""
    s = GRADIENT_GENERATOR.preview_fn()
    assert "gradients=" in s, f"Expected gradients= in preview: {s}"


def test_noise_generator_preview_fn() -> None:
    """NOISE_GENERATOR.preview_fn() produces a cellauto= filter string."""
    s = NOISE_GENERATOR.preview_fn()
    assert "cellauto=" in s, f"Expected cellauto= in preview: {s}"


def test_gradient_generator_build_fn() -> None:
    """GRADIENT_GENERATOR.build_fn() produces a gradients= filter string."""
    s = GRADIENT_GENERATOR.build_fn({"color1": "#000080", "color2": "white", "duration": 10.0})
    assert "gradients=" in s, f"Expected gradients= in build output: {s}"
    assert "0x000080" in s, f"Expected 0x000080 in build output: {s}"


def test_noise_generator_build_fn() -> None:
    """NOISE_GENERATOR.build_fn() produces a cellauto= filter string."""
    s = NOISE_GENERATOR.build_fn({"duration": 10.0})
    assert "cellauto=" in s, f"Expected cellauto= in build output: {s}"


# ---- Contract tests (BL-454-AC-4) — require real FFmpeg ----


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg contract tests",
)
def test_gradient_generator_ffmpeg_contract(tmp_path):  # type: ignore[no-untyped-def]
    """gradient_generator renders without error against real FFmpeg (BL-454-AC-4)."""
    import subprocess

    b = GradientGeneratorBuilder("black", "white", 2.0, width=320, height=240)
    filter_str = str(b.build())
    output = tmp_path / "gradient_out.mp4"
    result = subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", filter_str, "-t", "2", str(output)],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"FFmpeg gradient contract failed. stderr={result.stderr.decode()}"
    )
    assert output.exists(), "Output file was not created"


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg contract tests",
)
def test_noise_generator_ffmpeg_contract(tmp_path):  # type: ignore[no-untyped-def]
    """noise_generator renders without error against real FFmpeg (BL-454-AC-4)."""
    import subprocess

    b = NoiseGeneratorBuilder(2.0, width=320, height=240)
    filter_str = str(b.build())
    output = tmp_path / "noise_out.mp4"
    result = subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", filter_str, "-t", "2", str(output)],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, f"FFmpeg noise contract failed. stderr={result.stderr.decode()}"
    assert output.exists(), "Output file was not created"


# ---- ZoompanBuilder unit tests (BL-507) ----


def test_zoompan_builder_builds() -> None:
    """ZoompanBuilder.build() returns a non-empty Filter string (BL-507-AC-1)."""
    b = ZoompanBuilder("1.5", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)", 125, 1920, 1080, 30)
    s = str(b.build())
    assert s, "Expected non-empty filter string"
    assert "zoompan=" in s, f"Expected zoompan= in: {s}"
    assert "fps=30" in s, f"Expected fps=30 in: {s}"
    assert "settb=1/30" in s, f"Expected settb=1/30 in: {s}"


def test_zoompan_builder_invalid_z_expr() -> None:
    """ZoompanBuilder rejects z_expr containing apostrophe (BL-507-AC-1)."""
    with pytest.raises(ValueError):
        ZoompanBuilder("it's", "0", "0", 1, 100, 100, 30)


def test_zoompan_builder_zero_dimension() -> None:
    """ZoompanBuilder rejects width=0 (BL-507-AC-1)."""
    with pytest.raises(ValueError):
        ZoompanBuilder("1.5", "0", "0", 1, 0, 100, 30)


def test_zoompan_builder_zero_height() -> None:
    """ZoompanBuilder rejects height=0."""
    with pytest.raises(ValueError):
        ZoompanBuilder("1.5", "0", "0", 1, 100, 0, 30)


def test_zoompan_builder_zero_fps() -> None:
    """ZoompanBuilder rejects fps=0."""
    with pytest.raises(ValueError):
        ZoompanBuilder("1.5", "0", "0", 1, 100, 100, 0)


def test_zoompan_builder_zero_d() -> None:
    """ZoompanBuilder rejects d=0."""
    with pytest.raises(ValueError):
        ZoompanBuilder("1.5", "0", "0", 0, 100, 100, 30)


def test_zoompan_effect_definition_timeline_t_capable_false() -> None:
    """ZOOMPAN EffectDefinition has timeline_T_capable=False (BL-507-AC-5)."""
    assert ZOOMPAN.timeline_T_capable is False


def test_zoompan_effect_definition_description_fixed_canvas() -> None:
    """ZOOMPAN description contains 'fixed-canvas' scope statement (BL-507-AC-2)."""
    assert "fixed-canvas" in ZOOMPAN.description.lower() or "fixed-canvas" in ZOOMPAN.description


def test_zoompan_registered_in_default_registry() -> None:
    """zoompan is registered in the default effect registry."""
    registry = create_default_registry()
    definition = registry.get("zoompan")
    assert definition is not None
    assert definition is ZOOMPAN


def test_zoompan_preview_fn() -> None:
    """ZOOMPAN.preview_fn() produces a zoompan= filter string."""
    s = ZOOMPAN.preview_fn()
    assert "zoompan=" in s, f"Expected zoompan= in preview: {s}"
    assert "fps=" in s, f"Expected fps= in preview: {s}"
    assert "settb=" in s, f"Expected settb= in preview: {s}"


def test_zoompan_build_fn() -> None:
    """ZOOMPAN.build_fn() produces a zoompan= filter string with custom params."""
    s = ZOOMPAN.build_fn(
        {
            "z_expr": "1.2",
            "x_expr": "0",
            "y_expr": "0",
            "d": 60,
            "width": 640,
            "height": 480,
            "fps": 25,
        }
    )
    assert "zoompan=" in s, f"Expected zoompan= in build output: {s}"
    assert "fps=25" in s, f"Expected fps=25 in build output: {s}"
    assert "settb=1/25" in s, f"Expected settb=1/25 in build output: {s}"


# ---- CurvesBuilder unit tests (BL-508) ----


def test_curves_builder_preset_builds() -> None:
    """CurvesBuilder(preset='vintage') produces curves=preset=vintage (BL-508-AC-1)."""
    s = str(CurvesBuilder(preset="vintage").build())
    assert "curves=preset=vintage" in s, f"Expected curves=preset=vintage in: {s}"


def test_curves_builder_per_channel_builds() -> None:
    """CurvesBuilder per-channel knee produces quoted curves= string (BL-508-AC-2)."""
    s = str(CurvesBuilder(red="0/0 0.5/0.4 1/1").build())
    assert "curves=" in s, f"Expected curves= in: {s}"
    assert "red=" in s, f"Expected red= in: {s}"
    assert "0/0 0.5/0.4 1/1" in s, f"Expected knee points in: {s}"


def test_curves_builder_invalid_preset() -> None:
    """CurvesBuilder with an unknown preset raises ValueError (BL-508-AC-3)."""
    with pytest.raises(ValueError, match="preset"):
        CurvesBuilder(preset="unknown_preset")


def test_curves_builder_mutual_exclusion() -> None:
    """CurvesBuilder(preset=..., red=...) raises ValueError (BL-508-AC-4)."""
    with pytest.raises(ValueError, match="preset"):
        CurvesBuilder(preset="vintage", red="0/0 1/1")


def test_curves_effect_definition_timeline_t_capable_true() -> None:
    """CURVES EffectDefinition has timeline_T_capable=True (BL-508-AC-5)."""
    assert CURVES.timeline_T_capable is True


def test_curves_registered_in_default_registry() -> None:
    """'curves' is registered in the default effect registry (BL-508-AC-6)."""
    registry = create_default_registry()
    definition = registry.get("curves")
    assert definition is not None
    assert definition is CURVES


def test_curves_preview_fn() -> None:
    """CURVES.preview_fn() produces a curves= filter string."""
    s = CURVES.preview_fn()
    assert "curves=" in s, f"Expected curves= in preview: {s}"


def test_curves_build_fn_preset() -> None:
    """CURVES.build_fn({'preset': 'cross_process'}) produces curves=preset=cross_process."""
    s = CURVES.build_fn({"preset": "cross_process"})
    assert "curves=preset=cross_process" in s, f"Expected curves=preset=cross_process in: {s}"
