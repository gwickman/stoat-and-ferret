# Timeline Position Calculations

## Goal
Implement pure Rust functions for timeline position math: frame-to-time conversion, time-to-frame conversion, and duration calculations.

## Requirements

### FR-001: Frame/Time Conversion
- Convert frame number to timestamp given frame rate
- Convert timestamp to frame number given frame rate
- Support common frame rates: 23.976, 24, 25, 29.97, 30, 50, 59.94, 60
- Handle fractional frame rates as rationals (e.g., 23.976 = 24000/1001)

### FR-002: Duration Calculations
- Calculate duration from in/out points
- Calculate end time from start + duration
- Calculate frame count from duration and frame rate

### FR-003: FrameRate Type
- Represent as numerator/denominator (rational)
- Provide constants for common rates
- Support custom rates

### FR-004: Position Type
- Internal representation as frame count (u64)
- Conversion methods to/from seconds (f64)
- Implement Ord for comparison

### FR-005: Duration Type
- Internal representation as frame count (u64)
- Factory method from start/end positions
- Conversion methods to/from seconds

## Non-Functional Requirements

### NFR-001: Performance
- All calculations must be O(1)
- No allocations in hot paths

### NFR-002: Precision
- Frame-accurate: no accumulated rounding errors
- Exact round-trip: frame -> time -> frame = original

## Acceptance Criteria
- [ ] Property tests verify round-trip conversion
- [ ] All common frame rates supported as constants
- [ ] No floating-point in core calculations
- [ ] Comprehensive unit tests for edge cases