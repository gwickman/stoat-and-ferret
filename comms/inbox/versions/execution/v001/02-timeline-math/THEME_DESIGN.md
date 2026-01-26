# Theme 2: timeline-math

## Overview
Implement pure Rust functions for timeline calculations. These are the foundational math operations that all video editing operations depend on. Emphasis on correctness through property-based testing.

## Context
Video editing requires frame-accurate timing. Floating-point arithmetic introduces cumulative errors. This theme establishes:
- Frame-based internal representation
- Rational frame rate handling
- Property-tested range arithmetic

## Architecture Decisions

### AD-001: Internal Representation
Use integer frame counts internally, not floating-point seconds:
- Avoids accumulated rounding errors
- Enables exact comparisons
- Frame rates as rational numbers (24000/1001 not 23.976)

### AD-002: Pure Functions
All timeline math functions are pure:
- No side effects
- No I/O
- Deterministic output for given input
- Enables exhaustive property testing

### AD-003: Error Handling
Use Result types with descriptive errors:
- No panics in library code
- Errors carry context for debugging
- Validation returns all errors, not just first

### AD-004: No Drop-Frame Timecode
Drop-frame timecode support deferred. Start with non-drop-frame only.

## Dependencies
- Theme 1 (project-foundation) must be complete
- proptest crate for property testing

## Risks
- Edge cases in range arithmetic

## Success Criteria
- All property tests pass
- Round-trip conversions are exact
- No floating-point in core calculations
- Clippy clean