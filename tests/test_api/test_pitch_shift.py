"""Tests for PitchShiftBuilder (BL-443: pitch-shift / formant control)."""

from __future__ import annotations

import math
import os

import pytest

from stoat_ferret_core import PitchShiftBuilder

# ---------------------------------------------------------------------------
# Unit tests (no FFmpeg required)
# ---------------------------------------------------------------------------


def test_pitch_shift_contains_arubberband() -> None:
    """build() produces an arubberband filter."""
    chain = PitchShiftBuilder(2.0).build()
    assert "arubberband" in str(chain)


def test_pitch_shift_factor_formula() -> None:
    """Pitch factor equals 2^(semitones/12)."""
    chain = PitchShiftBuilder(2.0).build()
    expected = 2 ** (2.0 / 12.0)
    assert f"{expected:.6f}" in str(chain)


def test_pitch_shift_zero_semitones_is_unity() -> None:
    """Zero semitones gives pitch factor 1.0."""
    chain = PitchShiftBuilder(0.0).build()
    assert "pitch=1.000000" in str(chain)


def test_pitch_shift_negative_semitones() -> None:
    """Negative semitones produces pitch factor below 1.0."""
    chain = PitchShiftBuilder(-12.0).build()
    # -12 semitones = one octave down = 0.5
    expected = 2 ** (-12.0 / 12.0)
    assert f"{expected:.6f}" in str(chain)


def test_pitch_shift_default_formant_is_shifted() -> None:
    """Default formant mode is 'shifted'."""
    b = PitchShiftBuilder(2.0)
    assert b.formant == "shifted"
    assert "formant=shifted" in str(b.build())


def test_pitch_shift_default_quality_is_quality() -> None:
    """Default quality mode is 'quality'."""
    b = PitchShiftBuilder(2.0)
    assert b.quality == "quality"
    assert "pitchq=quality" in str(b.build())


def test_pitch_shift_with_formant_preserved() -> None:
    """with_formant('preserved') sets formant=preserved in the filter."""
    chain = PitchShiftBuilder(3.0).with_formant("preserved").build()
    assert "formant=preserved" in str(chain)


def test_pitch_shift_with_quality_speedy() -> None:
    """with_quality('speedy') sets pitchq=speedy."""
    chain = PitchShiftBuilder(1.0).with_quality("speedy").build()
    assert "pitchq=speedy" in str(chain)


def test_pitch_shift_semitones_property() -> None:
    """semitones property returns the configured value."""
    b = PitchShiftBuilder(-3.0)
    assert b.semitones == -3.0


def test_pitch_shift_out_of_range_raises() -> None:
    """Semitones outside [-24, 24] raises ValueError."""
    with pytest.raises(ValueError):
        PitchShiftBuilder(25.0)
    with pytest.raises(ValueError):
        PitchShiftBuilder(-25.0)


def test_pitch_shift_boundary_values_accepted() -> None:
    """Boundary values ±24 are accepted."""
    assert PitchShiftBuilder(24.0).semitones == 24.0
    assert PitchShiftBuilder(-24.0).semitones == -24.0


def test_pitch_shift_invalid_formant_raises() -> None:
    """Invalid formant raises ValueError."""
    with pytest.raises(ValueError):
        PitchShiftBuilder(2.0).with_formant("natural")


def test_pitch_shift_invalid_quality_raises() -> None:
    """Invalid quality raises ValueError."""
    with pytest.raises(ValueError):
        PitchShiftBuilder(2.0).with_quality("best")


def test_pitch_shift_repr() -> None:
    """__repr__ includes semitones, formant, and quality."""
    b = PitchShiftBuilder(2.5).with_formant("preserved").with_quality("speedy")
    r = repr(b)
    assert "PitchShiftBuilder" in r
    assert "2.5" in r
    assert "preserved" in r
    assert "speedy" in r


# ---------------------------------------------------------------------------
# FFmpeg contract tests (require real FFmpeg binary with libRubberBand)
# ---------------------------------------------------------------------------

_FFMPEG_TESTS = pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)


@_FFMPEG_TESTS
def test_pitch_shift_renders_voice(tmp_path: object) -> None:
    """PitchShiftBuilder renders a voice-like sine without FFmpeg errors."""
    import subprocess
    from pathlib import Path

    from stoat_ferret_core import build_generator_render_command

    src = str(Path(str(tmp_path)) / "voice.wav")
    out = str(Path(str(tmp_path)) / "shifted.wav")

    src_cmd = build_generator_render_command(
        '{"type": "sine", "frequency": 200.0}', 2.0, src
    )
    subprocess.run(["ffmpeg"] + src_cmd.args(), capture_output=True, check=True)

    chain = PitchShiftBuilder(2.0).with_formant("preserved").build()
    result = subprocess.run(
        ["ffmpeg", "-i", src, "-af", str(chain), out],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"pitch shift render failed: {result.stderr[-500:]}"
    assert Path(out).stat().st_size > 0
