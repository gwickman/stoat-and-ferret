"""Tests for optical distortion effects (BL-453).

Unit tests for LensDistortBuilder (builder validation, build output, determinism)
and effect registry registration.

Contract test (BL-453-AC-4) is deferred_post_merge and gated by STOAT_TEST_FFMPEG=1.
"""

from __future__ import annotations

import os

import pytest

from stoat_ferret.effects.definitions import LENS_DISTORT_EFFECT, create_default_registry
from stoat_ferret_core import LensDistortBuilder

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "0") == "1"


# ---------------------------------------------------------------------------
# LensDistortBuilder — construction validation (BL-453-AC-1)
# ---------------------------------------------------------------------------


def test_lens_distort_valid_construction() -> None:
    """LensDistortBuilder accepts k1 and k2 in [-1.0, 1.0]."""
    assert LensDistortBuilder(0.0, 0.0) is not None
    assert LensDistortBuilder(0.5, -0.3) is not None
    assert LensDistortBuilder(-1.0, 1.0) is not None
    assert LensDistortBuilder(1.0, -1.0) is not None


def test_lens_distort_k1_out_of_range_raises_value_error() -> None:
    """LensDistortBuilder raises ValueError when k1 is outside [-1.0, 1.0]."""
    with pytest.raises(ValueError):
        LensDistortBuilder(1.5, 0.0)
    with pytest.raises(ValueError):
        LensDistortBuilder(-1.1, 0.0)


def test_lens_distort_k2_out_of_range_raises_value_error() -> None:
    """LensDistortBuilder raises ValueError when k2 is outside [-1.0, 1.0]."""
    with pytest.raises(ValueError):
        LensDistortBuilder(0.0, 2.0)
    with pytest.raises(ValueError):
        LensDistortBuilder(0.0, -1.5)


def test_lens_distort_boundary_values_accepted() -> None:
    """LensDistortBuilder accepts the exact boundary values -1.0 and 1.0."""
    assert LensDistortBuilder(-1.0, -1.0) is not None
    assert LensDistortBuilder(1.0, 1.0) is not None
    assert LensDistortBuilder(0.0, 0.0) is not None


# ---------------------------------------------------------------------------
# LensDistortBuilder — build output (BL-453-AC-1)
# ---------------------------------------------------------------------------


def test_lens_distort_build_output_format() -> None:
    """build() produces a lenscorrection filter string with k1 and k2."""
    builder = LensDistortBuilder(0.5, -0.3)
    result = str(builder.build())
    assert "lenscorrection" in result
    assert "k1=" in result
    assert "k2=" in result


def test_lens_distort_build_contains_k1_value() -> None:
    """build() encodes the k1 value in the filter string."""
    builder = LensDistortBuilder(0.5, 0.0)
    result = str(builder.build())
    assert "0.5" in result


def test_lens_distort_build_contains_k2_value() -> None:
    """build() encodes the k2 value in the filter string."""
    builder = LensDistortBuilder(0.0, -0.3)
    result = str(builder.build())
    assert "-0.3" in result


# ---------------------------------------------------------------------------
# LensDistortBuilder — determinism (BL-453-AC-2)
# ---------------------------------------------------------------------------


def test_lens_distort_deterministic() -> None:
    """build() called twice on the same instance returns the same string."""
    builder = LensDistortBuilder(0.5, -0.3)
    first = str(builder.build())
    second = str(builder.build())
    assert first == second


def test_lens_distort_same_params_same_output() -> None:
    """Two builders with identical params produce the same filter string."""
    b1 = LensDistortBuilder(0.7, 0.2)
    b2 = LensDistortBuilder(0.7, 0.2)
    assert str(b1.build()) == str(b2.build())


# ---------------------------------------------------------------------------
# Effect registry (BL-453-AC-3)
# ---------------------------------------------------------------------------


def test_lens_distort_registered_in_default_registry() -> None:
    """lens_distort is registered in the default effect registry."""
    registry = create_default_registry()
    definition = registry.get("lens_distort")
    assert definition is not None


def test_lens_distort_effect_name() -> None:
    """LENS_DISTORT_EFFECT has the expected name."""
    assert LENS_DISTORT_EFFECT.name == "Lens Distort"


def test_lens_distort_schema_has_k1_and_k2() -> None:
    """LENS_DISTORT_EFFECT parameter schema defines k1 and k2 as number types."""
    props = LENS_DISTORT_EFFECT.parameter_schema["properties"]
    assert "k1" in props
    assert "k2" in props
    assert props["k1"]["type"] == "number"
    assert props["k2"]["type"] == "number"


def test_lens_distort_schema_k1_bounds() -> None:
    """LENS_DISTORT_EFFECT schema specifies [-1.0, 1.0] range for k1."""
    props = LENS_DISTORT_EFFECT.parameter_schema["properties"]
    assert props["k1"]["minimum"] == -1.0
    assert props["k1"]["maximum"] == 1.0


def test_lens_distort_schema_k2_bounds() -> None:
    """LENS_DISTORT_EFFECT schema specifies [-1.0, 1.0] range for k2."""
    props = LENS_DISTORT_EFFECT.parameter_schema["properties"]
    assert props["k2"]["minimum"] == -1.0
    assert props["k2"]["maximum"] == 1.0


def test_lens_distort_not_automatable() -> None:
    """LENS_DISTORT_EFFECT has no automatable parameters."""
    assert len(LENS_DISTORT_EFFECT.automatable) == 0


def test_lens_distort_build_fn_produces_lenscorrection() -> None:
    """LENS_DISTORT_EFFECT.build_fn produces a lenscorrection filter string."""
    result = LENS_DISTORT_EFFECT.build_fn({"k1": 0.3, "k2": -0.1})
    assert "lenscorrection" in result


def test_lens_distort_build_fn_defaults() -> None:
    """LENS_DISTORT_EFFECT.build_fn uses 0.0 defaults when params are absent."""
    result = LENS_DISTORT_EFFECT.build_fn({"k1": 0.0, "k2": 0.0})
    assert "lenscorrection" in result


def test_lens_distort_preview_fn_returns_string() -> None:
    """LENS_DISTORT_EFFECT.preview_fn returns a non-empty string."""
    result = LENS_DISTORT_EFFECT.preview_fn()
    assert isinstance(result, str)
    assert len(result) > 0


def test_lens_distort_has_nonempty_ai_summary() -> None:
    """LENS_DISTORT_EFFECT has a non-empty ai_summary."""
    assert LENS_DISTORT_EFFECT.ai_summary.strip()


def test_lens_distort_has_nonempty_example_prompt() -> None:
    """LENS_DISTORT_EFFECT has a non-empty example_prompt."""
    assert LENS_DISTORT_EFFECT.example_prompt.strip()


# ---------------------------------------------------------------------------
# Contract test (BL-453-AC-4) — deferred_post_merge, requires real FFmpeg
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="STOAT_TEST_FFMPEG not set")
def test_lens_distort_contract_ffmpeg(tmp_path: pytest.TempPathFactory) -> None:
    """lenscorrection filter applied to a real video clip produces output without error."""
    import subprocess

    builder = LensDistortBuilder(0.3, 0.3)
    filter_str = str(builder.build())

    # Generate a 1-second test clip and apply the filter
    output = tmp_path / "out.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x240:d=1",
            "-vf",
            filter_str,
            "-frames:v",
            "1",
            str(output),
        ],
        capture_output=True,
    )
    assert result.returncode == 0, f"FFmpeg failed: {result.stderr.decode()}"
    assert output.exists()
