# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for FramerateConvertBuilder and FRAMERATE_CONVERT effect definition (BL-448).

Covers:
- Filter string generation for all three modes (AC-1: target fps, AC-2: mode strings)
- Validation: invalid target_fps (≤0) raises ValueError
- EffectDefinition registration, preview_fn, build_fn
- FFmpeg-gated contract test using blend mode (AC-3)
"""

from __future__ import annotations

import os

import pytest

from stoat_ferret_core import FramerateConvertBuilder, FramerateMode

# ---------------------------------------------------------------------------
# Filter string generation — unit tests (BL-448-AC-1 / AC-2)
# ---------------------------------------------------------------------------


def test_framerate_convert_blend_30fps() -> None:
    """Blend mode at 30 fps produces minterpolate=fps=30:mi_mode=blend (AC-1/2)."""
    b = FramerateConvertBuilder(30.0, FramerateMode.Blend)
    assert str(b.build()) == "minterpolate=fps=30:mi_mode=blend"


def test_framerate_convert_blend_60fps() -> None:
    """Blend mode at 60 fps produces minterpolate=fps=60:mi_mode=blend."""
    b = FramerateConvertBuilder(60.0, FramerateMode.Blend)
    assert str(b.build()) == "minterpolate=fps=60:mi_mode=blend"


def test_framerate_convert_optical_flow_30fps() -> None:
    """OpticalFlow mode at 30 fps produces minterpolate=fps=30:mi_mode=mci (AC-2)."""
    b = FramerateConvertBuilder(30.0, FramerateMode.OpticalFlow)
    assert str(b.build()) == "minterpolate=fps=30:mi_mode=mci"


def test_framerate_convert_optical_flow_60fps() -> None:
    """OpticalFlow mode at 60 fps produces minterpolate=fps=60:mi_mode=mci."""
    b = FramerateConvertBuilder(60.0, FramerateMode.OpticalFlow)
    assert str(b.build()) == "minterpolate=fps=60:mi_mode=mci"


def test_framerate_convert_duplicate_24fps() -> None:
    """Duplicate mode at 24 fps produces framerate=fps=24 (AC-2)."""
    b = FramerateConvertBuilder(24.0, FramerateMode.Duplicate)
    assert str(b.build()) == "framerate=fps=24"


def test_framerate_convert_duplicate_30fps() -> None:
    """Duplicate mode at 30 fps produces framerate=fps=30."""
    b = FramerateConvertBuilder(30.0, FramerateMode.Duplicate)
    assert str(b.build()) == "framerate=fps=30"


def test_framerate_convert_fractional_fps() -> None:
    """Fractional fps (23.976) is serialized correctly without trailing zeros."""
    b = FramerateConvertBuilder(23.976, FramerateMode.Blend)
    result = str(b.build())
    assert result.startswith("minterpolate=fps=23.976"), f"Got: {result}"
    assert "mi_mode=blend" in result


def test_framerate_convert_target_fps_getter() -> None:
    """target_fps property returns the value passed to the constructor."""
    b = FramerateConvertBuilder(60.0, FramerateMode.Blend)
    assert abs(b.target_fps - 60.0) < 1e-9


def test_framerate_convert_mode_getter() -> None:
    """mode property returns the mode passed to the constructor."""
    b = FramerateConvertBuilder(30.0, FramerateMode.OpticalFlow)
    assert b.mode == FramerateMode.OpticalFlow


# ---------------------------------------------------------------------------
# Validation — invalid target_fps
# ---------------------------------------------------------------------------


def test_framerate_convert_zero_fps_rejected() -> None:
    """FramerateConvertBuilder with target_fps=0.0 raises ValueError."""
    with pytest.raises((ValueError, RuntimeError)):
        FramerateConvertBuilder(0.0, FramerateMode.Blend)


def test_framerate_convert_negative_fps_rejected() -> None:
    """FramerateConvertBuilder with target_fps < 0 raises ValueError."""
    with pytest.raises((ValueError, RuntimeError)):
        FramerateConvertBuilder(-1.0, FramerateMode.Blend)


# ---------------------------------------------------------------------------
# FramerateMode string helpers
# ---------------------------------------------------------------------------


def test_framerate_mode_from_str_blend() -> None:
    """FramerateMode.from_str('blend') returns Blend variant."""
    assert FramerateMode.from_str("blend") == FramerateMode.Blend


def test_framerate_mode_from_str_optical_flow() -> None:
    """FramerateMode.from_str('optical_flow') returns OpticalFlow variant."""
    assert FramerateMode.from_str("optical_flow") == FramerateMode.OpticalFlow


def test_framerate_mode_from_str_duplicate() -> None:
    """FramerateMode.from_str('duplicate') returns Duplicate variant."""
    assert FramerateMode.from_str("duplicate") == FramerateMode.Duplicate


def test_framerate_mode_from_str_invalid() -> None:
    """FramerateMode.from_str with unknown name raises ValueError."""
    with pytest.raises((ValueError, RuntimeError)):
        FramerateMode.from_str("invalid_mode")


def test_framerate_mode_str_blend() -> None:
    """str(FramerateMode.Blend) returns 'blend'."""
    assert str(FramerateMode.Blend) == "blend"


def test_framerate_mode_str_optical_flow() -> None:
    """str(FramerateMode.OpticalFlow) returns 'optical_flow'."""
    assert str(FramerateMode.OpticalFlow) == "optical_flow"


def test_framerate_mode_str_duplicate() -> None:
    """str(FramerateMode.Duplicate) returns 'duplicate'."""
    assert str(FramerateMode.Duplicate) == "duplicate"


# ---------------------------------------------------------------------------
# EffectDefinition tests
# ---------------------------------------------------------------------------


def test_framerate_convert_registered_in_default_registry() -> None:
    """FRAMERATE_CONVERT is registered under 'framerate_convert' in the default registry."""
    from stoat_ferret.effects.definitions import create_default_registry

    registry = create_default_registry()
    assert registry.get("framerate_convert") is not None


def test_framerate_convert_preview_fn_blend_mode() -> None:
    """FRAMERATE_CONVERT.preview_fn returns a non-empty filter string."""
    from stoat_ferret.effects.definitions import FRAMERATE_CONVERT

    result = FRAMERATE_CONVERT.preview_fn()
    assert isinstance(result, str)
    assert len(result) > 0


def test_framerate_convert_build_fn_blend_mode() -> None:
    """FRAMERATE_CONVERT.build_fn with blend mode returns correct filter."""
    from stoat_ferret.effects.definitions import FRAMERATE_CONVERT

    result = FRAMERATE_CONVERT.build_fn({"target_fps": 60.0, "mode": "blend"})
    assert result == "minterpolate=fps=60:mi_mode=blend"


def test_framerate_convert_build_fn_optical_flow() -> None:
    """FRAMERATE_CONVERT.build_fn with optical_flow mode returns mci filter."""
    from stoat_ferret.effects.definitions import FRAMERATE_CONVERT

    result = FRAMERATE_CONVERT.build_fn({"target_fps": 30.0, "mode": "optical_flow"})
    assert result == "minterpolate=fps=30:mi_mode=mci"


def test_framerate_convert_build_fn_duplicate_mode() -> None:
    """FRAMERATE_CONVERT.build_fn with duplicate mode returns framerate filter."""
    from stoat_ferret.effects.definitions import FRAMERATE_CONVERT

    result = FRAMERATE_CONVERT.build_fn({"target_fps": 24.0, "mode": "duplicate"})
    assert result == "framerate=fps=24"


def test_framerate_convert_schema_has_required_fields() -> None:
    """FRAMERATE_CONVERT parameter schema requires target_fps and mode."""
    from stoat_ferret.effects.definitions import FRAMERATE_CONVERT

    required = FRAMERATE_CONVERT.parameter_schema.get("required", [])
    assert "target_fps" in required
    assert "mode" in required


def test_framerate_convert_schema_mode_enum() -> None:
    """FRAMERATE_CONVERT parameter schema enumerates the three mode values."""
    from stoat_ferret.effects.definitions import FRAMERATE_CONVERT

    enum_vals = (
        FRAMERATE_CONVERT.parameter_schema["properties"]["mode"].get("enum", [])  # type: ignore[index]
    )
    assert set(enum_vals) == {"duplicate", "blend", "optical_flow"}


# ---------------------------------------------------------------------------
# FFmpeg-gated contract test (BL-448-AC-3)
# ---------------------------------------------------------------------------

_FFMPEG_GATED = pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)


@_FFMPEG_GATED
def test_framerate_convert_blend_ffmpeg_contract(tmp_path: str) -> None:
    """FramerateConvertBuilder blend mode exits with code 0 on a short fixture (BL-448-AC-3).

    Discharge command:
        STOAT_TEST_FFMPEG=1 uv run pytest \
            tests/test_effects_framerate.py::test_framerate_convert_blend_ffmpeg_contract -v
    """
    import subprocess
    from pathlib import Path

    tmp = Path(str(tmp_path))
    source = tmp / "source.mp4"
    converted = tmp / "converted.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=160x90:rate=15",
            "-c:v",
            "libx264",
            "-t",
            "2",
            str(source),
        ],
        check=True,
        capture_output=True,
    )

    filter_str = str(FramerateConvertBuilder(30.0, FramerateMode.Blend).build())
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vf",
            filter_str,
            str(converted),
        ],
        check=True,
        capture_output=True,
    )

    assert converted.exists(), "converted output file must exist after render"
    assert converted.stat().st_size > 0, "converted output must be non-empty"
