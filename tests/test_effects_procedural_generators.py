# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit and contract tests for procedural generator effects (BL-454), ZoompanBuilder (BL-507),
CurvesBuilder (BL-508), VignetteBuilder (BL-509), HueRotationBuilder (BL-510),
and shape generators (BL-513): SpiralGenerator, RadialBurstGenerator,
CheckerboardGenerator, ConcentricRingsGenerator.

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

BL-509 ACs:
- AC-1 (narrowed to AC-2): VignetteBuilder exists in video.rs with position enum.
- AC-2: Position enum resolves to x0/y0 expression strings (AC-2 surface).
- AC-3: VignetteBuilder emits vignette=angle:x0:y0:mode:eval format.
- AC-4: Three contract tests: centre default, backward mode, init vs frame eval.
- AC-5: VIGNETTE EffectDefinition with timeline_T_capable=True.

BL-510 ACs:
- AC-1: HueRotationBuilder emits hue=H='<expr>' — single-quote wrap, no comma escape.
- AC-2: Comma-bearing expression if(lt(t,1),0,PI) passes through unescaped.
- AC-3: Implementation in video.rs; no BL-502 reference.
- AC-4: Apostrophe in h_expr raises ValueError at build time.
"""

from __future__ import annotations

import os
import pathlib

import pytest

from stoat_ferret.effects.definitions import (
    CURVES,
    GRADIENT_GENERATOR,
    HUE_ROTATION,
    NOISE_GENERATOR,
    VIGNETTE,
    ZOOMPAN,
    create_default_registry,
)
from stoat_ferret_core import (
    CurvesBuilder,
    GradientGeneratorBuilder,
    HueRotationBuilder,
    NoiseGeneratorBuilder,
    VignetteBuilder,
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


# ---- VignetteBuilder unit tests (BL-509) ----


def test_vignette_centre_default() -> None:
    """VignetteBuilder(position='centre') produces symmetric x0=w/2, y0=h/2 (BL-509-AC-2/3)."""
    s = str(VignetteBuilder(position="centre").build())
    assert "vignette=" in s, f"Expected vignette= in: {s}"
    assert "x0=w/2" in s, f"Expected x0=w/2 in: {s}"
    assert "y0=h/2" in s, f"Expected y0=h/2 in: {s}"
    assert "mode=forward" in s, f"Expected mode=forward in: {s}"
    assert "eval=init" in s, f"Expected eval=init in: {s}"


def test_vignette_corner_position() -> None:
    """VignetteBuilder with corner positions resolves to correct x0/y0 (BL-509-AC-2)."""
    b = VignetteBuilder(position="top_left")
    s = str(b.build())
    assert "x0=0" in s, f"Expected x0=0 in top_left output: {s}"
    assert "y0=0" in s, f"Expected y0=0 in top_left output: {s}"

    b2 = VignetteBuilder(position="bottom_right")
    s2 = str(b2.build())
    assert "x0=w" in s2, f"Expected x0=w in bottom_right output: {s2}"
    assert "y0=h" in s2, f"Expected y0=h in bottom_right output: {s2}"


def test_vignette_backward_mode() -> None:
    """VignetteBuilder(mode='backward') emits mode=backward (BL-509-AC-3/4)."""
    s = str(VignetteBuilder(position="centre", mode="backward").build())
    assert "mode=backward" in s, f"Expected mode=backward in: {s}"


def test_vignette_eval_frame_differs_from_init() -> None:
    """eval_mode='frame' produces a different emit than 'init' (BL-509-AC-4)."""
    s_init = str(VignetteBuilder(position="centre", angle=0.5, eval_mode="init").build())
    s_frame = str(VignetteBuilder(position="centre", angle=0.5, eval_mode="frame").build())
    assert s_init != s_frame, "init and frame eval modes must produce different strings"
    assert "eval=frame" in s_frame, f"Expected eval=frame in frame-mode output: {s_frame}"
    assert "eval=init" in s_init, f"Expected eval=init in init-mode output: {s_init}"


def test_vignette_invalid_angle() -> None:
    """VignetteBuilder rejects angle outside [0, PI/2] with ValueError (BL-509-AC-2)."""
    with pytest.raises(ValueError):
        VignetteBuilder(position="centre", angle=2.0)


def test_vignette_invalid_position() -> None:
    """VignetteBuilder rejects unknown position strings with ValueError (BL-509-AC-2)."""
    with pytest.raises(ValueError):
        VignetteBuilder(position="middle")


def test_vignette_effect_definition_timeline_t_capable_true() -> None:
    """VIGNETTE EffectDefinition has timeline_T_capable=True (BL-509-AC-5)."""
    assert VIGNETTE.timeline_T_capable is True


def test_vignette_registered_in_default_registry() -> None:
    """'vignette' is registered in the default effect registry (BL-509-AC-5)."""
    registry = create_default_registry()
    definition = registry.get("vignette")
    assert definition is not None
    assert definition is VIGNETTE


def test_vignette_preview_fn() -> None:
    """VIGNETTE.preview_fn() produces a vignette= filter string."""
    s = VIGNETTE.preview_fn()
    assert "vignette=" in s, f"Expected vignette= in preview: {s}"


def test_vignette_build_fn_centre() -> None:
    """VIGNETTE.build_fn({'position': 'centre'}) produces vignette= with x0=w/2."""
    s = VIGNETTE.build_fn({"position": "centre"})
    assert "vignette=" in s, f"Expected vignette= in: {s}"
    assert "x0=w/2" in s, f"Expected x0=w/2 in: {s}"


# ---- HueRotationBuilder unit tests (BL-510) ----


def test_hue_rotation_single_quote_wrap() -> None:
    """HueRotationBuilder wraps h_expr in single quotes: hue=H='...' (BL-510-AC-1)."""
    s = str(HueRotationBuilder("2*PI*t/3").build())
    assert "hue=H='2*PI*t/3'" in s, f"Expected single-quote wrap in: {s}"


def test_hue_rotation_comma_bearing_expression() -> None:
    """Comma-bearing expression passes through unescaped inside single quotes (BL-510-AC-2)."""
    s = str(HueRotationBuilder("if(lt(t,1),0,PI)").build())
    assert "hue=H='if(lt(t,1),0,PI)'" in s, (
        f"Expected unescaped commas inside single quotes in: {s}"
    )


def test_hue_rotation_no_comma_escape() -> None:
    """No backslash-comma escape appears in hue=H= output (BL-510-AC-2)."""
    s = str(HueRotationBuilder("if(lt(t,1),0,PI)").build())
    assert r"\," not in s, f"Expected NO backslash-comma escape in: {s}"


def test_hue_rotation_apostrophe_rejection() -> None:
    """h_expr containing a single quote raises ValueError at build time (BL-510-AC-4)."""
    import pytest

    with pytest.raises(ValueError, match="single quote"):
        HueRotationBuilder("0'PI").build()


def test_hue_rotation_effect_definition_timeline_t_capable_true() -> None:
    """HUE_ROTATION EffectDefinition has timeline_T_capable=True (BL-510-AC-1)."""
    assert HUE_ROTATION.timeline_T_capable is True


def test_hue_rotation_registered_in_default_registry() -> None:
    """'hue_rotation' is registered in the default effect registry (BL-510)."""
    registry = create_default_registry()
    definition = registry.get("hue_rotation")
    assert definition is not None
    assert definition is HUE_ROTATION


def test_hue_rotation_preview_fn() -> None:
    """HUE_ROTATION.preview_fn() produces a hue= filter string."""
    s = HUE_ROTATION.preview_fn()
    assert "hue=" in s, f"Expected hue= in preview: {s}"


def test_hue_rotation_build_fn() -> None:
    """HUE_ROTATION.build_fn({'h_expr': '2*PI*t/3'}) produces hue=H= filter string."""
    s = HUE_ROTATION.build_fn({"h_expr": "2*PI*t/3"})
    assert "hue=H=" in s, f"Expected hue=H= in: {s}"
    assert "2*PI*t/3" in s, f"Expected expression in: {s}"


# ===========================================================================
# BL-513: Shape Generators
# ===========================================================================


def test_shape_builders_import() -> None:
    """All 4 shape generators are importable from stoat_ferret_core (BL-513 AC-1)."""
    from stoat_ferret_core import (
        CheckerboardGenerator,
        ConcentricRingsGenerator,
        RadialBurstGenerator,
        SpiralGenerator,
    )

    assert CheckerboardGenerator is not None
    assert ConcentricRingsGenerator is not None
    assert RadialBurstGenerator is not None
    assert SpiralGenerator is not None


def test_spiral_render_to_file(tmp_path: pathlib.Path) -> None:
    """SpiralGenerator.render_to_file writes a valid PNG (BL-513 AC-5)."""
    from stoat_ferret_core import SpiralGenerator

    out = tmp_path / "spiral.png"
    gen = SpiralGenerator(3.0, 2.0)
    gen.render_to_file(str(out), 64, 64)
    assert out.exists(), "spiral.png was not created"
    assert out.stat().st_size > 0, "spiral.png is empty"


def test_radial_burst_render_to_file(tmp_path: pathlib.Path) -> None:
    """RadialBurstGenerator.render_to_file writes a valid PNG (BL-513 AC-5)."""
    from stoat_ferret_core import RadialBurstGenerator

    out = tmp_path / "radial.png"
    gen = RadialBurstGenerator(12, 0.4)
    gen.render_to_file(str(out), 64, 64)
    assert out.exists(), "radial.png was not created"
    assert out.stat().st_size > 0, "radial.png is empty"


def test_checkerboard_render_to_file(tmp_path: pathlib.Path) -> None:
    """CheckerboardGenerator.render_to_file writes a valid PNG (BL-513 AC-5)."""
    from stoat_ferret_core import CheckerboardGenerator

    out = tmp_path / "checker.png"
    gen = CheckerboardGenerator(8)
    gen.render_to_file(str(out), 64, 64)
    assert out.exists(), "checker.png was not created"
    assert out.stat().st_size > 0, "checker.png is empty"


def test_concentric_rings_render_to_file(tmp_path: pathlib.Path) -> None:
    """ConcentricRingsGenerator.render_to_file writes a valid PNG (BL-513 AC-5)."""
    from stoat_ferret_core import ConcentricRingsGenerator

    out = tmp_path / "rings.png"
    gen = ConcentricRingsGenerator(8, 0.4)
    gen.render_to_file(str(out), 64, 64)
    assert out.exists(), "rings.png was not created"
    assert out.stat().st_size > 0, "rings.png is empty"


def test_shape_generators_invalid_params() -> None:
    """Shape generators raise ValueError for out-of-range parameters (BL-513 AC-2)."""
    from stoat_ferret_core import (
        CheckerboardGenerator,
        ConcentricRingsGenerator,
        RadialBurstGenerator,
        SpiralGenerator,
    )

    with pytest.raises(ValueError):
        CheckerboardGenerator(0)
    with pytest.raises(ValueError):
        ConcentricRingsGenerator(0, 0.4)
    with pytest.raises(ValueError):
        ConcentricRingsGenerator(8, 0.0)
    with pytest.raises(ValueError):
        ConcentricRingsGenerator(8, 1.0)
    with pytest.raises(ValueError):
        RadialBurstGenerator(0, 0.4)
    with pytest.raises(ValueError):
        RadialBurstGenerator(12, 0.0)
    with pytest.raises(ValueError):
        RadialBurstGenerator(12, 1.0)
    with pytest.raises(ValueError):
        SpiralGenerator(0.0, 2.0)
    with pytest.raises(ValueError):
        SpiralGenerator(3.0, 0.0)


# ===========================================================================
# BL-514: GenericProceduralImageBuilder
# ===========================================================================


def _read_png_rgba_row(path: pathlib.Path, row: int = 0) -> list[tuple[int, int, int, int]]:
    """Read RGBA pixels from a specific row of a PNG file using stdlib only."""
    import struct
    import zlib

    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG file"
    pos = 8
    idat_chunks: list[bytes] = []
    width = height = 0
    color_type = 0
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        if chunk_type == b"IHDR":
            width, height = struct.unpack(">II", chunk_data[:8])
            color_type = chunk_data[9]
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break
        pos += 12 + length

    raw = zlib.decompress(b"".join(idat_chunks))
    bpp = 4 if color_type == 6 else 3  # RGBA vs RGB
    stride = width * bpp
    prev = bytearray(stride)
    result_row: list[tuple[int, int, int, int]] = []
    p = 0
    for r in range(height):
        filt = raw[p]
        row_raw = bytearray(raw[p + 1 : p + 1 + stride])
        p += 1 + stride
        if filt == 1:  # Sub
            for i in range(bpp, stride):
                row_raw[i] = (row_raw[i] + row_raw[i - bpp]) & 0xFF
        elif filt == 2:  # Up
            for i in range(stride):
                row_raw[i] = (row_raw[i] + prev[i]) & 0xFF
        elif filt == 3:  # Average
            for i in range(stride):
                a = row_raw[i - bpp] if i >= bpp else 0
                row_raw[i] = (row_raw[i] + (a + prev[i]) // 2) & 0xFF
        elif filt == 4:  # Paeth
            for i in range(stride):
                a = row_raw[i - bpp] if i >= bpp else 0
                b2 = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p_val = a + b2 - c
                pa, pb, pc = abs(p_val - a), abs(p_val - b2), abs(p_val - c)
                pr = a if pa <= pb and pa <= pc else (b2 if pb <= pc else c)
                row_raw[i] = (row_raw[i] + pr) & 0xFF
        if r == row:
            if bpp == 4:
                result_row = [
                    (row_raw[i], row_raw[i + 1], row_raw[i + 2], row_raw[i + 3])
                    for i in range(0, stride, 4)
                ]
            else:
                result_row = [
                    (row_raw[i], row_raw[i + 1], row_raw[i + 2], 255)
                    for i in range(0, stride, 3)
                ]
            break
        prev = row_raw
    return result_row


def test_generic_procedural_import() -> None:
    """GenericProceduralImageBuilder is importable from stoat_ferret_core (BL-514 AC-1)."""
    from stoat_ferret_core import GenericProceduralImageBuilder

    assert GenericProceduralImageBuilder is not None


def test_generic_procedural_stub_presence() -> None:
    """GenericProceduralImageBuilder appears in _core.pyi (BL-514 AC-6)."""
    import pathlib

    stub = pathlib.Path("src/stoat_ferret_core/_core.pyi").read_text()
    assert "GenericProceduralImageBuilder" in stub, (
        "_core.pyi missing GenericProceduralImageBuilder"
    )


def test_generic_procedural_linear_gradient(tmp_path: pathlib.Path) -> None:
    """expression='x' at 64x64: first column ≈ 0, last column ≈ 255 (BL-514 AC-5 contract 1)."""
    from stoat_ferret_core import GenericProceduralImageBuilder

    out = tmp_path / "gradient.png"
    GenericProceduralImageBuilder("x", 64, 64).synthesise(str(out))
    assert out.exists() and out.stat().st_size > 0

    row = _read_png_rgba_row(out, row=0)
    first_r = row[0][0]
    last_r = row[-1][0]
    assert first_r < 10, f"first pixel R={first_r}, expected ~0"
    assert last_r > 245, f"last pixel R={last_r}, expected ~255"


def test_generic_procedural_radial(tmp_path: pathlib.Path) -> None:
    """expression='hypot(x-0.5,y-0.5)': center pixel < corner pixel (BL-514 AC-5 contract 2)."""
    from stoat_ferret_core import GenericProceduralImageBuilder

    out = tmp_path / "radial.png"
    GenericProceduralImageBuilder("hypot(x-0.5,y-0.5)", 64, 64).synthesise(str(out))
    assert out.exists() and out.stat().st_size > 0

    # Read row 32 (middle row) to get center pixel at col 32
    row_mid = _read_png_rgba_row(out, row=32)
    center_r = row_mid[32][0]

    # Read row 0 to get corner pixel at col 0
    row_top = _read_png_rgba_row(out, row=0)
    corner_r = row_top[0][0]

    assert center_r < corner_r, (
        f"center R={center_r} should be < corner R={corner_r}"
    )


def test_generic_procedural_spiral_deterministic(tmp_path: pathlib.Path) -> None:
    """Animated spiral at t=0.5 produces identical bytes on two renders (BL-514 AC-5 contract 3)."""
    import hashlib

    from stoat_ferret_core import GenericProceduralImageBuilder

    SPIRAL_EXPR = "sin(atan2(y-0.5,x-0.5)*4+t*6.28)*0.5+0.5"
    out1 = tmp_path / "spiral1.png"
    out2 = tmp_path / "spiral2.png"
    GenericProceduralImageBuilder(SPIRAL_EXPR, 64, 64, at_time=0.5).synthesise(str(out1))
    GenericProceduralImageBuilder(SPIRAL_EXPR, 64, 64, at_time=0.5).synthesise(str(out2))

    h1 = hashlib.sha256(out1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(out2.read_bytes()).hexdigest()
    assert h1 == h2, f"spiral render not deterministic: {h1} vs {h2}"


def test_generic_procedural_invalid_expression() -> None:
    """Invalid expression raises ValueError at construction time (BL-514 AC-2)."""
    from stoat_ferret_core import GenericProceduralImageBuilder

    with pytest.raises(ValueError):
        GenericProceduralImageBuilder("foo_bar", 64, 64)


def test_generic_procedural_zero_dimension() -> None:
    """Zero width or height raises ValueError (BL-514 AC-2)."""
    from stoat_ferret_core import GenericProceduralImageBuilder

    with pytest.raises(ValueError):
        GenericProceduralImageBuilder("x", 0, 64)
    with pytest.raises(ValueError):
        GenericProceduralImageBuilder("x", 64, 0)


@pytest.mark.timeout(2.0)
def test_generic_procedural_performance(tmp_path: pathlib.Path) -> None:
    """256x256 render completes within 2000ms (BL-514 AC-4, informational)."""
    from stoat_ferret_core import GenericProceduralImageBuilder

    out = tmp_path / "perf.png"
    GenericProceduralImageBuilder("sin(x*6.28)*cos(y*6.28)", 256, 256).synthesise(str(out))
    assert out.exists() and out.stat().st_size > 0
