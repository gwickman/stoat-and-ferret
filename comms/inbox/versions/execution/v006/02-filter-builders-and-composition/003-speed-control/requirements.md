# Requirements: speed-control

## Goal

Implement setpts/atempo builders with automatic atempo chaining for speeds above 2x.

## Background

Backlog Item: BL-041

No Rust types exist for video speed (setpts) or audio speed (atempo) control. M2.3 requires speed adjustment from 0.25x to 4.0x. The atempo filter maxes at 2.0x and requires automatic chaining for higher speeds — a non-obvious FFmpeg detail that should be encapsulated in the builder.

## Functional Requirements

**FR-001: Video speed via setpts**
- Adjustable speed via setpts with factor range 0.25x-4.0x
- Expression: `PTS/factor` (frame-rate independent)
- AC: setpts generates correct `PTS/factor` expression for all valid speed factors

**FR-002: Audio speed via atempo**
- Audio speed adjustment with automatic chaining for factors above 2.0x
- Factors >2.0x decomposed into chained atempo filters (e.g., 3x = atempo=2.0,atempo=1.5)
- AC: Single atempo for factors <=2.0x; chained atempo for factors >2.0x with correct decomposition

**FR-003: Audio drop option**
- Option to drop audio entirely instead of speed-adjusting it
- AC: Audio drop mode generates video-only speed filter without atempo

**FR-004: Validation**
- Reject out-of-range values with helpful error messages
- Use existing `validate_speed()` from Rust sanitize module for range validation (0.25-4.0)
- AC: Values outside 0.25-4.0 range produce clear error messages

**FR-005: Edge case handling**
- Correct handling of 1x (no-op), boundary values (0.25x, 4.0x), and extreme speeds
- AC: Unit tests cover all edge cases with correct output

**FR-006: PyO3 bindings**
- Expose speed control builders to Python with type stubs
- AC: Python code can build speed control filters identically to Rust

## Non-Functional Requirements

**NFR-001: Frame-rate independence**
- Speed control operates on PTS values, independent of frame rate
- AC: Same speed factor produces correct results for any frame rate (23.976, 29.97, 30, 60 fps)

**NFR-002: Test coverage**
- Module-level Rust coverage >90%
- AC: `cargo tarpaulin` reports >90% for the speed control module

## Out of Scope

- Variable speed (speed changes within a single clip)
- Audio pitch correction during speed changes
- Reverse playback (negative speed factors)

## Test Requirements

- **Unit tests:** setpts video speed (factor range, PTS expression generation), atempo audio speed (auto-chaining for >2x, decomposition correctness), audio drop option, validation (out-of-range rejection), edge cases (1x no-op, boundary values 0.25x/4.0x)

Reference: `See comms/outbox/versions/design/v006/004-research/ for supporting evidence`