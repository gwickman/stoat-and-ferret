# C4 Code Level: Example Tests

## Overview

- **Name**: Example Tests
- **Description**: Reference property-based tests demonstrating invariant-first design with Hypothesis
- **Location**: [tests/examples/](../../tests/examples/)
- **Language**: Python (pytest, Hypothesis)
- **Purpose**: Provides copy-paste templates for writing property tests on domain objects (Video, Clip), demonstrating the invariant-first approach to test design

## Code Elements

### Test Inventory

| File | Tests | Coverage |
|------|-------|----------|
| test_property_example.py | 4 | Video and Clip model invariants |
| **Total** | **4** | **Property-based testing patterns** |

### test_property_example.py

#### Reusable Hypothesis Strategies (lines 30-44)

- `frame_counts = st.integers(min_value=0, max_value=10_000_000)`
  - Non-negative frame counts in realistic range

- `positive_frame_counts = st.integers(min_value=1, max_value=10_000_000)`
  - Positive frame counts (for durations > 0)

- `frame_rate_numerators = st.integers(min_value=1, max_value=240_000)`
  - Valid numerator component of frame rate (1 to 240,000 fps)

- `frame_rate_denominators = st.integers(min_value=1, max_value=1001)`
  - Valid denominator component (standard video frame rates like 23.976, 29.97)

- `dimensions = st.integers(min_value=1, max_value=16384)`
  - Video dimensions (1×1 to 16K)

- `file_sizes = st.integers(min_value=1, max_value=10**12)`
  - File sizes up to 1TB

#### Property Tests

**PT-001: Video.frame_rate Always Positive** (lines 52-78)
- Test: `test_video_frame_rate_always_positive(numerator, denominator)`
- Invariant: `frame_rate_numerator > 0 AND frame_rate_denominator > 0 => frame_rate > 0`
- Marks: `@pytest.mark.property`, `@given()`
- Generates: 100+ examples from strategy combinations

**PT-002: Video.duration_seconds Round Trip** (lines 86-120)
- Test: `test_video_duration_seconds_round_trip(duration_frames, numerator, denominator)`
- Invariant: `duration_seconds * frame_rate ≈ duration_frames` (within 1e-6 tolerance)
- Purpose: Validates round-trip consistency: frames → seconds → frames
- Marks: `@pytest.mark.property`, `@given()`
- Floating-point tolerance: `abs(reconstructed_frames - duration_frames) < 1e-6`

**PT-003: Clip Duration Non-Negative** (lines 128-152)
- Test: `test_clip_duration_non_negative(in_point, extra)`
- Invariant: `out_point >= in_point => (out_point - in_point) >= 0`
- Strategy: Generates `out_point = in_point + extra` to guarantee constraint
- Marks: `@pytest.mark.property`, `@given()`

**PT-004: Clip Timeline Sort Stability** (lines 160-187)
- Test: `test_clip_timeline_sort_stability(positions: list[int])`
- Invariant: Sorting clips by timeline_position produces non-decreasing sequence
- Strategy: `st.lists(frame_counts, min_size=2, max_size=20)`
- Marks: `@pytest.mark.property`, `@given()`, `@settings(max_examples=50)`
- Verifies sort stability across randomized position lists

#### Test Configuration

- Pytest marker: `@pytest.mark.property` — Distinguish property tests from unit tests
- Default Hypothesis settings: 100 examples per test
- PT-004 override: `@settings(max_examples=50)` — Reduce examples for list generation cost

## Dependencies

### Internal Dependencies
- `stoat_ferret.db.models` (Video, Clip)
  - Video.__init__, Video.frame_rate, Video.duration_seconds
  - Clip.__init__, Clip.out_point - Clip.in_point

### External Dependencies
- pytest (6.0+)
- hypothesis (>=6.0)
  - strategies: integers, lists
  - decorators: given, settings

## Relationships

```mermaid
---
title: Property Test Architecture
---
classDiagram
    namespace StrategyLibrary {
        class FrameStrategies {
            +frame_counts
            +positive_frame_counts
        }
        class RateStrategies {
            +frame_rate_numerators
            +frame_rate_denominators
        }
        class DimensionStrategies {
            +dimensions
            +file_sizes
        }
    }
    namespace PropertyTests {
        class VideoProperties {
            +PT-001: frame_rate positive
            +PT-002: duration_seconds roundtrip
        }
        class ClipProperties {
            +PT-003: duration non-negative
            +PT-004: sort stability
        }
    }
    namespace UnderTest {
        class Video {
            +frame_rate: float
            +duration_seconds: float
        }
        class Clip {
            +timeline_position: int
            +in_point, out_point: int
        }
    }

    VideoProperties --> FrameStrategies : uses @given
    VideoProperties --> RateStrategies : uses @given
    VideoProperties --> Video : tests invariants
    ClipProperties --> FrameStrategies : uses @given
    ClipProperties --> Clip : tests invariants
    RateStrategies --> "Hypothesis" : powered by
    DimensionStrategies --> "Hypothesis" : powered by
```

## Notes

- **Invariant-First Approach**: Properties are identified before implementation. Tests articulate domain constraints.
- **Template Reference**: These tests serve as copy-paste templates for new features. See docs/auto-dev/PROCESS/generic/02-REQUIREMENTS.md for guidance.
- **Hypothesis Powers**: Finds edge cases humans miss (0 denominator prevented by strategy, floating-point rounding caught by tolerance)
- **Floating-Point Safety**: PT-002 uses 1e-6 tolerance for round-trip validation
- **pytest.mark.property**: Allows filtering with `pytest -m property` to run only property tests
- **Realistic Ranges**: Strategies use domain-informed bounds (e.g., frame rates up to 240,000 fps for specialty video)
