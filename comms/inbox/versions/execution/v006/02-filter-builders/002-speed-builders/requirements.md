# Requirements: speed-builders

## Goal

setpts and atempo filter builders with automatic atempo chaining for speeds above 2.0x.

## Background

Backlog Item: BL-041

No Rust types exist for video speed (setpts) or audio speed (atempo) control. M2.3 requires speed adjustment from 0.25x to 4.0x. The atempo filter maxes at 2.0x quality and requires automatic chaining for higher speeds — a non-obvious FFmpeg detail that should be encapsulated in the builder. Without these builders, speed control must be hand-coded with raw filter strings for each speed value.

## Functional Requirements

### FR-001: Video Speed via setpts

Video speed adjustable via `setpts` with factor range 0.25x–4.0x. Formula: `PTS * (1.0 / speed_factor)`. Examples: 2x = `setpts=0.5*PTS`, 0.5x = `setpts=2.0*PTS`.

**Acceptance criteria:** Video speed adjustable via setpts with factor range 0.25x–4.0x.

### FR-002: Audio Speed via atempo with Chaining

Audio speed via atempo with automatic chaining for factors above 2.0x or below 0.5x. Each chained instance stays within [0.5, 2.0] for quality. Chaining formula: `N = floor(log2(speed))` stages of 2.0 + remainder. Examples: 4.0x = `atempo=2.0,atempo=2.0`; 3.0x = `atempo=2.0,atempo=1.5`; 0.25x = `atempo=0.5,atempo=0.5`.

**Acceptance criteria:** Audio speed via atempo with automatic chaining for factors above 2.0x.

### FR-003: Drop Audio Option

Option to drop audio entirely instead of speed-adjusting it. Useful for timelapse-style effects.

**Acceptance criteria:** Option to drop audio entirely instead of speed-adjusting it.

### FR-004: Input Validation

Validation rejects out-of-range values with helpful error messages. Speed range [0.25, 4.0] matching existing `validate_speed()` in `sanitize/mod.rs`.

**Acceptance criteria:** Validation rejects out-of-range values with helpful error messages.

### FR-005: Edge Cases

Unit tests cover edge cases: 1x (no-op), boundary values (0.25, 4.0), extreme speeds, and the atempo chaining boundary at 2.0x.

**Acceptance criteria:** Unit tests cover edge cases: 1x (no-op), boundary values, extreme speeds.

## Non-Functional Requirements

### NFR-001: Test Coverage

New speed module targets >90% coverage. CI threshold remains at 75%.

## Out of Scope

- Speed ramping (variable speed over time)
- Audio pitch correction after speed change
- Reverse playback

## Test Requirements

- Unit tests for setpts formula at various speeds
- Unit tests for atempo chaining logic (single instance, chained, boundary)
- Unit tests for drop-audio option
- Unit tests for validation error messages
- Edge case tests (1x no-op, 0.25x, 4.0x, 2.0x boundary)
- Proptest for speed range validation
- PyO3 binding tests
- Type stub regeneration and verification

## Sub-tasks

- Impact #4: Run `cargo run --bin stub_gen` after adding PyO3 bindings

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.