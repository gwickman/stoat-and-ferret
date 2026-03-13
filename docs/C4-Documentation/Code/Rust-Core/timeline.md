# C4 Code Level: Timeline Module

**Source:** `rust/stoat_ferret_core/src/timeline/`
**Component:** Rust Core

## Purpose

Provides frame-accurate timeline mathematics for video editing without floating-point precision issues. All timeline values use integer frame counts internally, with conversions to/from seconds using rational frame rates.

## Public Interface

### Structs (PyO3 Classes)

#### `FrameRate`
Represents frame rate as a rational number (numerator/denominator).

**Construction:**
- `FrameRate::new(numerator: u32, denominator: u32) -> Option<Self>` — Create custom frame rate; returns None if denominator is zero
- Predefined constants: `FPS_23_976`, `FPS_24`, `FPS_25`, `FPS_29_97`, `FPS_30`, `FPS_50`, `FPS_59_94`, `FPS_60`

**Methods:**
- `numerator() -> u32` — Get numerator (Python: getter `numerator`)
- `denominator() -> u32` — Get denominator (Python: getter `denominator`)
- `frames_per_second() -> f64` — Convert to floating-point fps (Python: getter `fps`)

**PyO3 Factory Methods:**
- `FrameRate.fps_23_976() -> FrameRate`
- `FrameRate.fps_24() -> FrameRate`
- `FrameRate.fps_25() -> FrameRate`
- `FrameRate.fps_29_97() -> FrameRate`
- `FrameRate.fps_30() -> FrameRate`
- `FrameRate.fps_50() -> FrameRate`
- `FrameRate.fps_59_94() -> FrameRate`
- `FrameRate.fps_60() -> FrameRate`

#### `Position`
Represents a point in time as a frame count.

**Construction:**
- `Position::from_frames(frames: u64) -> Self` — Create from frame count
- `Position::from_seconds(seconds: f64, fps: FrameRate) -> Self` — Create from seconds; uses rounding for nearest frame

**Constants:**
- `Position::ZERO` — Position at frame 0

**Methods:**
- `frames() -> u64` — Get frame count (Python: getter `frames`)
- `to_seconds(fps: FrameRate) -> f64` — Convert to seconds

**PyO3 Methods:**
- `Position(frames: u64)` — Constructor
- `from_secs(seconds: f64, fps: FrameRate) -> Position` — Static method
- `as_secs(fps: FrameRate) -> f64` — Instance method
- `zero() -> Position` — Static factory

**Comparison operators:** `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__`

#### `Duration`
Represents a span of time as a frame count.

**Construction:**
- `Duration::from_frames(frames: u64) -> Self` — Create from frame count
- `Duration::from_seconds(seconds: f64, fps: FrameRate) -> Self` — Create from seconds; uses rounding

**Constants:**
- `Duration::ZERO` — Zero duration (0 frames)

**Static Methods:**
- `Duration::between(start: Position, end: Position) -> Option<Self>` — Calculate duration; returns None if end < start

**Methods:**
- `frames() -> u64` — Get frame count (Python: getter `frames`)
- `to_seconds(fps: FrameRate) -> f64` — Convert to seconds
- `end_position(start: Position) -> Position` — Calculate end position from start position

**PyO3 Methods:**
- `Duration(frames: u64)` — Constructor
- `from_secs(seconds: f64, fps: FrameRate) -> Duration` — Static method
- `as_secs(fps: FrameRate) -> f64` — Instance method
- `between_positions(start: Position, end: Position) -> Duration` — Static method (raises ValueError if end < start)
- `end_pos(start: Position) -> Position` — Instance method
- `zero() -> Duration` — Static factory

**Comparison operators:** `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__`

#### `TimeRange`
Represents a half-open time range [start, end) with overlap and gap detection.

**Construction:**
- `TimeRange::new(start: Position, end: Position) -> Result<Self, RangeError>` — Create range; returns error if end <= start

**Methods:**
- `start() -> Position` — Start position (Python: getter `start`)
- `end() -> Position` — End position (Python: getter `end`)
- `duration() -> Duration` — Duration of range (Python: getter `duration`)
- `overlaps(other: &TimeRange) -> bool` — Check if ranges share frames
- `adjacent(other: &TimeRange) -> bool` — Check if ranges meet exactly
- `overlap(other: &TimeRange) -> Option<TimeRange>` — Get overlap region
- `gap(other: &TimeRange) -> Option<TimeRange>` — Get gap between ranges
- `intersection(other: &TimeRange) -> Option<TimeRange>` — Alias for overlap
- `union(other: &TimeRange) -> Option<TimeRange>` — Merge if contiguous
- `difference(other: &TimeRange) -> Vec<TimeRange>` — Subtract range (0-2 results)

**PyO3 Methods:**
- All methods listed above have corresponding `py_` versions with same signatures

### Functions

#### Free Functions (Exported from timeline::)

- **`find_gaps(ranges: &[TimeRange]) -> Vec<TimeRange>`**
  - Finds gaps between non-overlapping portions
  - Time complexity: O(n log n) due to sorting
  - Python binding: `find_gaps(ranges: List[TimeRange]) -> List[TimeRange]`

- **`merge_ranges(ranges: &[TimeRange]) -> Vec<TimeRange>`**
  - Merges overlapping and adjacent ranges
  - Returns minimal non-overlapping set covering same time
  - Time complexity: O(n log n)
  - Python binding: `merge_ranges(ranges: List[TimeRange]) -> List[TimeRange]`

- **`total_coverage(ranges: &[TimeRange]) -> Duration`**
  - Calculates total duration covered by ranges
  - Overlapping portions counted once
  - Time complexity: O(n log n)
  - Python binding: `total_coverage(ranges: List[TimeRange]) -> Duration`

### Enums

#### `RangeError`

- `RangeError::InvalidBounds` — end position is not greater than start position

## Dependencies

### Internal Crate Dependencies

None — timeline module has no dependencies on other crate modules. It is a self-contained primitive library.

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings (`prelude`, attribute macros)
- **pyo3_stub_gen** — Stub generation support
- **proptest** — Property-based testing (test-only)

## Key Implementation Details

### Frame-Accurate Arithmetic

All calculations use integer frame counts (`u64`) to avoid floating-point precision errors. Conversions between frames and seconds use rational arithmetic:

- **Frames to seconds:** `seconds = frames * (denominator / numerator)`
- **Seconds to frames:** `frames = round(seconds * (numerator / denominator))`

### Rational Frame Rates

Frame rates like 23.976 fps (NTSC film) are represented exactly as fractions:
- 23.976 fps = 24000/1001
- 29.97 fps (NTSC video) = 30000/1001
- 59.94 fps = 60000/1001

This ensures exact calculations without accumulated floating-point error.

### Half-Open Interval Semantics

TimeRange uses [start, end) semantics:
- Includes start position (frame 0)
- Excludes end position (frame 100 means frames 0-99)
- Adjacent ranges can be concatenated without overlap or gap

### Overlap and Gap Detection

- **overlaps:** `self.start < other.end && other.start < self.end`
- **adjacent:** `self.end == other.start || other.end == self.start`
- Two adjacent ranges have no gap between them

### Round-Trip Precision

All types pass property-based round-trip tests:
- `frames -> seconds -> frames` produces identical frame count
- Works for both integer frame rates (24 fps) and fractional rates (23.976 fps)

## Relationships

**Used by:**
- `clip` module — Uses Position and Duration for clip in/out points
- `compose` module — Uses TimeRange for timeline composition
- Python video editor UI — Uses all types for timeline visualization and manipulation

**Uses:**
- (No internal dependencies)

## Testing

Comprehensive test suite includes:

1. **Unit tests** for each type and method
2. **Property-based tests** (proptest) for round-trip conversions and invariants:
   - Frame-to-seconds-to-frame round trips produce exact results
   - Duration between positions is inverse of end position calculation
   - All overlap/gap/union operations are symmetric
   - Merged ranges maintain same total coverage
   - Merged ranges have no overlaps

3. **Integration tests** for typical video editing workflows:
   - Set in-point at 5 seconds, out-point at 10.5 seconds
   - Calculate clip duration
   - Place clip at timeline position 1 minute
   - Verify timeline end position

## Notes

- **Frame Count Limits:** Uses `u64` for frame counts, supporting videos up to ~18 million years at 60 fps
- **Resolution-Independent:** All calculations are resolution-independent; frame counts translate to pixels only at render time
- **No Timezone Issues:** Unlike system time, timeline frames have no timezone or DST complications
- **Zero-Indexed:** Frames are 0-indexed: frame 0 is the first frame
- **Custom FrameRate Normalization:** FrameRate does not normalize fractions; `FrameRate::new(60, 2)` != `FrameRate::new(30, 1)`. This preserves source intent for exact round-trip conversions.
