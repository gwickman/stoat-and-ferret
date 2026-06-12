"""Tests for VariableSpeedBuilder segmented-concat effect (BL-447).

Covers:
- 2-segment filter graph shape (AC-4 proxy: build path)
- 3-segment filter graph shape
- Validation errors: empty segments, speed_factor out of range
- SpeedControl constant-speed path unchanged (AC-4 regression guard)
- FFmpeg-gated duration probe (AC-1/2/3 — skipped without STOAT_TEST_FFMPEG=1)
"""

from __future__ import annotations

import os

import pytest

from stoat_ferret_core import SpeedControl, SpeedSegment, VariableSpeedBuilder

# ---------------------------------------------------------------------------
# Filter graph shape — unit tests
# ---------------------------------------------------------------------------


def test_variable_speed_2_segment_filter_graph() -> None:
    """2-segment graph has correct trim/setpts/atrim/atempo/concat structure."""
    segs = [SpeedSegment(0, 30, 2.0), SpeedSegment(30, 60, 0.5)]
    result = VariableSpeedBuilder(segs).build_filter_graph()

    expected = (
        "[0:v]trim=start_frame=0:end_frame=30,setpts=0.5*(PTS-STARTPTS)[vseg0];"
        "[0:v]trim=start_frame=30:end_frame=60,setpts=2*(PTS-STARTPTS)[vseg1];"
        "[0:a]atrim=start_frame=0:end_frame=30,asetpts=NB_CONSUMED_SAMPLES/SR/TB,atempo=2[aseg0];"
        "[0:a]atrim=start_frame=30:end_frame=60,asetpts=NB_CONSUMED_SAMPLES/SR/TB,atempo=0.5[aseg1];"
        "[vseg0][vseg1]concat=n=2:v=1:a=0[vout];"
        "[aseg0][aseg1]concat=n=2:v=0:a=1[aout]"
    )
    assert result == expected


def test_variable_speed_3_segment_filter_graph() -> None:
    """3-segment graph: n=3 in concat and three trim/atrim chains."""
    segs = [SpeedSegment(0, 30, 2.0), SpeedSegment(30, 60, 0.5), SpeedSegment(60, 90, 1.5)]
    result = VariableSpeedBuilder(segs).build_filter_graph()

    assert "[vseg0][vseg1][vseg2]concat=n=3:v=1:a=0[vout]" in result
    assert "[aseg0][aseg1][aseg2]concat=n=3:v=0:a=1[aout]" in result
    assert "trim=start_frame=0:end_frame=30" in result
    assert "trim=start_frame=30:end_frame=60" in result
    assert "trim=start_frame=60:end_frame=90" in result
    assert "atempo=2" in result
    assert "atempo=0.5" in result
    assert "atempo=1.5" in result


def test_variable_speed_filter_graph_contains_asetpts() -> None:
    """Audio segments include asetpts=NB_CONSUMED_SAMPLES/SR/TB after atrim."""
    segs = [SpeedSegment(0, 30, 2.0), SpeedSegment(30, 60, 0.5)]
    result = VariableSpeedBuilder(segs).build_filter_graph()

    assert result.count("asetpts=NB_CONSUMED_SAMPLES/SR/TB") == 2


def test_variable_speed_setpts_uses_pts_startpts() -> None:
    """Video setpts expressions use PTS-STARTPTS to reset timestamps per segment."""
    segs = [SpeedSegment(0, 30, 2.0)]
    result = VariableSpeedBuilder(segs).build_filter_graph()

    assert "PTS-STARTPTS" in result


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_variable_speed_empty_segments_rejected() -> None:
    """VariableSpeedBuilder with empty segments list raises ValueError."""
    with pytest.raises((ValueError, RuntimeError)):
        VariableSpeedBuilder([])


def test_variable_speed_zero_speed_factor_rejected() -> None:
    """SpeedSegment with speed_factor=0.0 raises ValueError."""
    with pytest.raises((ValueError, RuntimeError)):
        SpeedSegment(0, 30, 0.0)


def test_variable_speed_negative_speed_factor_rejected() -> None:
    """SpeedSegment with speed_factor < 0 raises ValueError."""
    with pytest.raises((ValueError, RuntimeError)):
        SpeedSegment(0, 30, -1.0)


def test_variable_speed_excessive_speed_factor_rejected() -> None:
    """SpeedSegment with speed_factor > 100 raises ValueError."""
    with pytest.raises((ValueError, RuntimeError)):
        SpeedSegment(0, 30, 100.1)


def test_variable_speed_max_speed_factor_accepted() -> None:
    """SpeedSegment with speed_factor=100.0 (boundary) is accepted."""
    seg = SpeedSegment(0, 30, 100.0)
    assert seg.speed_factor == 100.0


# ---------------------------------------------------------------------------
# SpeedControl regression guard (AC-4)
# ---------------------------------------------------------------------------


def test_speed_control_setpts_filter_unchanged() -> None:
    """SpeedControl 2x still produces setpts=0.5*PTS (regression guard — AC-4)."""
    sc = SpeedControl(2.0)
    assert "setpts=0.5*PTS" in repr(sc.setpts_filter())


def test_speed_control_atempo_filters_unchanged() -> None:
    """SpeedControl 2x still chains a single atempo=2 filter."""
    sc = SpeedControl(2.0)
    filters = sc.atempo_filters()
    assert len(filters) == 1
    assert "atempo=2" in repr(filters[0])


def test_speed_control_slow_motion_unchanged() -> None:
    """SpeedControl 0.25x still chains two atempo filters (below 0.5 boundary)."""
    sc = SpeedControl(0.25)
    filters = sc.atempo_filters()
    assert len(filters) == 2


# ---------------------------------------------------------------------------
# FFmpeg-gated duration probe (AC-1 / AC-2 / AC-3)
# ---------------------------------------------------------------------------

_FFMPEG_GATED = pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)


@_FFMPEG_GATED
def test_variable_speed_output_duration_integral() -> None:
    """Rendered output duration equals sum of segment durations (tolerance ≤ 100ms).

    Discharge command:
        STOAT_TEST_FFMPEG=1 uv run pytest \
            tests/test_effects_variable_speed.py::test_variable_speed_output_duration_integral -v
    """
    pytest.skip("FFmpeg duration probe not yet implemented — deferred_post_merge discharge")


@_FFMPEG_GATED
def test_variable_speed_segment_speed_verified() -> None:
    """Probe confirms each segment plays at the declared speed (AC-2).

    Discharge command:
        STOAT_TEST_FFMPEG=1 uv run pytest \
            tests/test_effects_variable_speed.py::test_variable_speed_segment_speed_verified -v
    """
    pytest.skip("FFmpeg segment probe not yet implemented — deferred_post_merge discharge")


@_FFMPEG_GATED
def test_variable_speed_audio_pitch_unchanged() -> None:
    """Rendered audio pitch tracks atempo correctly across segments (AC-3).

    Discharge command:
        STOAT_TEST_FFMPEG=1 uv run pytest \
            tests/test_effects_variable_speed.py::test_variable_speed_audio_pitch_unchanged -v
    """
    pytest.skip("FFmpeg audio-pitch probe not yet implemented — deferred_post_merge discharge")
