# C4 Code Level: Timeline Mathematics

## Overview
- **Name**: Timeline Mathematics for Frame-Accurate Video Editing
- **Description**: Provides Rust types and operations for precise frame-based timeline calculations with no floating-point precision loss
- **Location**: rust/stoat_ferret_core/src/timeline
- **Language**: Rust
- **Purpose**: Enable frame-accurate positioning, duration calculation, and time range operations for video editing without floating-point errors
- **Parent Component**: [Rust Core Engine](./c4-component-rust-core-engine.md)

## Code Elements

### Structs

- `FrameRate`
  - Description: Represents frame rate as a rational number (numerator/denominator) to handle fractional rates like 23.976 fps (24000/1001) and 29.97 fps (30000/1001) precisely
  - Location: framerate.rs:32
  - Fields: `numerator: u32`, `denominator: u32`
  - Constants: `FPS_23_976`, `FPS_24`, `FPS_25`, `FPS_29_97`, `FPS_30`, `FPS_50`, `FPS_59_94`, `FPS_60`
  - Key Methods: `new(num, denom) -> Option<Self>`, `frames_per_second() -> f64`, `numerator() -> u32`, `denominator() -> u32`

- `Position`
  - Description: Represents a point in time on the timeline as a frame count (u64), ensuring frame-accurate positioning without floating-point errors
  - Location: position.rs:36
  - Fields: `frames: u64` (newtype wrapper)
  - Constant: `ZERO = Position(0)`
  - Key Methods: `from_frames(frames) -> Self`, `from_seconds(seconds, fps) -> Self`, `frames() -> u64`, `to_seconds(fps) -> f64`

- `Duration`
  - Description: Represents a span of time as a frame count (u64), supporting conversions to/from seconds at a specified frame rate
  - Location: duration.rs:38
  - Fields: `frames: u64` (newtype wrapper)
  - Constant: `ZERO = Duration(0)`
  - Key Methods: `from_frames(frames) -> Self`, `from_seconds(seconds, fps) -> Self`, `between(start, end) -> Option<Self>`, `frames() -> u64`, `to_seconds(fps) -> f64`, `end_position(start) -> Position`

- `TimeRange`
  - Description: Represents a half-open interval [start, end) on the timeline with operations for overlap detection, gap calculation, and set operations (union, intersection, difference)
  - Location: range.rs:54
  - Fields: `start: Position`, `end: Position`
  - Key Methods: `new(start, end) -> Result<Self>`, `start() -> Position`, `end() -> Position`, `duration() -> Duration`, `overlaps(other) -> bool`, `adjacent(other) -> bool`, `overlap(other) -> Option<TimeRange>`, `gap(other) -> Option<TimeRange>`, `intersection(other) -> Option<TimeRange>`, `union(other) -> Option<TimeRange>`, `difference(other) -> Vec<TimeRange>`

### Enums

- `RangeError`
  - Description: Error type for time range operations
  - Location: range.rs:14
  - Variant: `InvalidBounds` - End position is not greater than start position

### Module-Level Functions

- `find_gaps(ranges: &[TimeRange]) -> Vec<TimeRange>`
  - Description: Finds gaps between non-overlapping portions of ranges (after sorting/merging)
  - Location: range.rs:443
  - Time Complexity: O(n log n)

- `merge_ranges(ranges: &[TimeRange]) -> Vec<TimeRange>`
  - Description: Merges overlapping and adjacent ranges into a minimal set of non-overlapping ranges
  - Location: range.rs:490
  - Time Complexity: O(n log n)

- `total_coverage(ranges: &[TimeRange]) -> Duration`
  - Description: Calculates total duration covered by ranges (accounting for overlaps)
  - Location: range.rs:531
  - Time Complexity: O(n log n)

## Dependencies

### Internal Dependencies
- `Position` ↔ `Duration` (Position/Duration conversions via `Duration::between()` and `Duration::end_position()`)
- `FrameRate` ← `Position`, `Duration` (used for second conversions in both)
- `TimeRange` ← `Position`, `Duration` (half-open interval with position boundaries and duration)
- `RangeError` ← `TimeRange` (error handling for range construction)
- Module exports: `mod.rs` re-exports all public types and functions

### External Dependencies
- `pyo3` (PyO3 bindings for Python interop)
- `pyo3_stub_gen::derive::gen_stub_pyclass` (automatic Python stub generation)
- Standard library: `std::cmp`, `std::fmt`, `std::error`
- Test dependencies: `proptest` (property-based testing)

## Relationships

```mermaid
---
title: Code Diagram for Timeline Module
---
classDiagram
    namespace Timeline {
        class FrameRate {
            -numerator: u32
            -denominator: u32
            +new(u32, u32) Option~Self~
            +frames_per_second() f64
            +numerator() u32
            +denominator() u32
        }
        class Position {
            -frames: u64
            +from_frames(u64) Self
            +from_seconds(f64, FrameRate) Self
            +frames() u64
            +to_seconds(FrameRate) f64
        }
        class Duration {
            -frames: u64
            +from_frames(u64) Self
            +from_seconds(f64, FrameRate) Self
            +between(Position, Position) Option~Self~
            +frames() u64
            +to_seconds(FrameRate) f64
            +end_position(Position) Position
        }
        class TimeRange {
            -start: Position
            -end: Position
            +new(Position, Position) Result~Self~
            +overlaps(TimeRange) bool
            +adjacent(TimeRange) bool
            +overlap(TimeRange) Option~Self~
            +gap(TimeRange) Option~Self~
            +union(TimeRange) Option~Self~
            +intersection(TimeRange) Option~Self~
            +difference(TimeRange) Vec~Self~
        }
        class RangeError {
            <<enum>>
            InvalidBounds
        }
    }
    
    Duration -->|uses| FrameRate: second conversions
    Position -->|uses| FrameRate: second conversions
    Duration -->|computes between| Position: interval math
    TimeRange -->|contains| Position: start/end boundaries
    TimeRange -->|computes| Duration: duration property
    TimeRange -->|returns| RangeError: error handling
    
    class RangeOps["Range Operations"]
    RangeOps --|uses| TimeRange: find_gaps, merge_ranges, total_coverage
```

## Notes

- All position and duration values use unsigned 64-bit frame counts internally to eliminate floating-point precision issues
- Frame rate is stored as a rational number (numerator/denominator) to handle fractional rates (NTSC timecode) exactly
- TimeRange uses half-open interval semantics [start, end) which matches video editing conventions
- All types derive standard Rust traits: `Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `Hash`
- All struct/function signatures are exposed to Python via PyO3 bindings with automatically generated stubs
- Extensive property-based testing via proptest validates round-trip conversions and invariants
