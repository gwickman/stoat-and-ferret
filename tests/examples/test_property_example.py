"""Example property tests demonstrating invariant-first design.

These tests show how to use Hypothesis for property-based testing with
stoat-and-ferret domain objects. They serve as a reference for writing
property tests in new features.

Invariant-first approach:
  1. Identify properties that must ALWAYS hold (before writing implementation).
  2. Express each property as a Hypothesis test with @given.
  3. Let Hypothesis find edge cases you wouldn't think to test manually.

See docs/auto-dev/PROCESS/generic/02-REQUIREMENTS.md for guidance on when
to include property tests in feature requirements.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stoat_ferret.db.models import Clip, Video

# ---------------------------------------------------------------------------
# Strategies: reusable generators for domain objects
# ---------------------------------------------------------------------------

# Frame counts: non-negative integers in a realistic range
frame_counts = st.integers(min_value=0, max_value=10_000_000)

# Positive frame counts (for durations that must be > 0)
positive_frame_counts = st.integers(min_value=1, max_value=10_000_000)

# Frame rate components: numerator > 0, denominator > 0
frame_rate_numerators = st.integers(min_value=1, max_value=240_000)
frame_rate_denominators = st.integers(min_value=1, max_value=1001)

# Video dimensions in realistic range
dimensions = st.integers(min_value=1, max_value=16384)

# File sizes: positive integers
file_sizes = st.integers(min_value=1, max_value=10**12)


# ---------------------------------------------------------------------------
# PT-001: Video.frame_rate is always positive when inputs are valid
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    numerator=frame_rate_numerators,
    denominator=frame_rate_denominators,
)
def test_video_frame_rate_always_positive(numerator: int, denominator: int) -> None:
    """Video.frame_rate is always positive for valid numerator/denominator.

    Invariant: frame_rate_numerator > 0 AND frame_rate_denominator > 0
               => frame_rate > 0
    """
    now = datetime.now(timezone.utc)
    video = Video(
        id="test",
        path="/test.mp4",
        filename="test.mp4",
        duration_frames=1000,
        frame_rate_numerator=numerator,
        frame_rate_denominator=denominator,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=1_000_000,
        created_at=now,
        updated_at=now,
    )
    assert video.frame_rate > 0


# ---------------------------------------------------------------------------
# PT-002: Video.duration_seconds is consistent with frames and frame rate
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    duration_frames=positive_frame_counts,
    numerator=frame_rate_numerators,
    denominator=frame_rate_denominators,
)
def test_video_duration_seconds_round_trip(
    duration_frames: int,
    numerator: int,
    denominator: int,
) -> None:
    """duration_seconds * frame_rate ≈ duration_frames (within floating-point tolerance).

    Invariant: duration_seconds * frame_rate == duration_frames
    This is a round-trip property — converting frames to seconds and back
    should yield the original frame count.
    """
    now = datetime.now(timezone.utc)
    video = Video(
        id="test",
        path="/test.mp4",
        filename="test.mp4",
        duration_frames=duration_frames,
        frame_rate_numerator=numerator,
        frame_rate_denominator=denominator,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=1_000_000,
        created_at=now,
        updated_at=now,
    )
    # Round-trip: frames -> seconds -> frames
    reconstructed_frames = video.duration_seconds * video.frame_rate
    assert abs(reconstructed_frames - duration_frames) < 1e-6


# ---------------------------------------------------------------------------
# PT-003: Clip duration is always non-negative when out_point >= in_point
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    in_point=frame_counts,
    extra=frame_counts,
)
def test_clip_duration_non_negative(in_point: int, extra: int) -> None:
    """Clip duration (out_point - in_point) is non-negative when out_point >= in_point.

    Invariant: out_point >= in_point => (out_point - in_point) >= 0
    We generate out_point as in_point + extra to guarantee the constraint.
    """
    out_point = in_point + extra
    now = datetime.now(timezone.utc)
    clip = Clip(
        id="test",
        project_id="proj",
        source_video_id="vid",
        in_point=in_point,
        out_point=out_point,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    duration = clip.out_point - clip.in_point
    assert duration >= 0


# ---------------------------------------------------------------------------
# PT-004: Clip ordering is preserved across timeline positions
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    positions=st.lists(frame_counts, min_size=2, max_size=20),
)
@settings(max_examples=50)
def test_clip_timeline_sort_stability(positions: list[int]) -> None:
    """Sorting clips by timeline_position is stable and deterministic.

    Invariant: sorting a list of clips by timeline_position always produces
    a non-decreasing sequence of positions.
    """
    now = datetime.now(timezone.utc)
    clips = [
        Clip(
            id=f"clip-{i}",
            project_id="proj",
            source_video_id="vid",
            in_point=0,
            out_point=100,
            timeline_position=pos,
            created_at=now,
            updated_at=now,
        )
        for i, pos in enumerate(positions)
    ]
    sorted_clips = sorted(clips, key=lambda c: c.timeline_position)
    for i in range(len(sorted_clips) - 1):
        assert sorted_clips[i].timeline_position <= sorted_clips[i + 1].timeline_position
