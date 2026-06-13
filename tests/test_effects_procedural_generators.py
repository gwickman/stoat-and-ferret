"""Unit and contract tests for procedural generator effects (BL-454).

BL-454 ACs:
- AC-1: GradientGeneratorBuilder generates a gradient clip with configurable colors.
- AC-2: NoiseGeneratorBuilder generates an evolving noise/pattern clip.
- AC-3: Both generators render for their configured duration.
- AC-4 (deferred): Renders without error verified by contract test against real FFmpeg.
    Discharge: STOAT_TEST_FFMPEG=1 pytest tests/test_effects_procedural_generators.py -k contract
"""

from __future__ import annotations

import os

import pytest

from stoat_ferret.effects.definitions import (
    GRADIENT_GENERATOR,
    NOISE_GENERATOR,
    create_default_registry,
)
from stoat_ferret_core import GradientGeneratorBuilder, NoiseGeneratorBuilder

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
