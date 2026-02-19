# Requirements: transition-filter-builders

## Goal

Build FadeBuilder, XfadeBuilder with TransitionType enum and AcrossfadeBuilder in Rust with PyO3 bindings, providing type-safe video/audio transition filter generation.

## Background

Backlog Item: BL-045

No Rust types exist for video transitions. M2.5 requires fade in, fade out, crossfade between clips, and xfade with selectable transition effects. Transitions are fundamental to video editing but currently have no type-safe builder. The v006 builder pattern (LRN-028) provides the template. Two-input filters (xfade, acrossfade) use the existing `FilterChain.input()` multi-input pattern proven through concat tests.

## Functional Requirements

**FR-001**: FadeBuilder supports fade in/out with configurable duration and color
- AC: `FadeBuilder::new("in", 3.0)` creates a 3-second fade-in
- AC: Supports `type`: `in` or `out`
- AC: Supports `duration` in seconds and `nb_frames` as alternative
- AC: Supports `color` parameter (named colors and hex #RRGGBB, default: "black")
- AC: Supports `alpha` mode for alpha channel fading
- AC: Supports `start_time` parameter
- AC: `.build()` returns `Filter` with correct fade syntax

**FR-002**: XfadeBuilder supports selectable effect types with duration and offset
- AC: `XfadeBuilder::new(TransitionType::Wipeleft, 2.0, 5.0)` creates a wipe-left transition
- AC: TransitionType enum has all 64 FFmpeg xfade variants
- AC: Duration validated in range 0.0-60.0 seconds
- AC: Offset parameter sets transition start relative to first input
- AC: Invalid transition type returns `PyValueError`
- AC: Two-input filter chain: `FilterChain::new().input(label1).input(label2).filter(xfade).output(out)`
- AC: `.build()` returns `Filter` with correct xfade syntax

**FR-003**: TransitionType enum provides type-safe transition selection
- AC: All 64 FFmpeg xfade variants represented as enum variants
- AC: String conversion round-trip: `TransitionType::from_str("wipeleft") == TransitionType::Wipeleft`
- AC: Python binding exposes enum variants as class attributes
- AC: Invalid string returns appropriate error

**FR-004**: AcrossfadeBuilder supports audio crossfade between inputs
- AC: `AcrossfadeBuilder::new(2.0)` creates a 2-second audio crossfade
- AC: Supports `duration` in seconds
- AC: Supports `curve1` and `curve2` parameters (same 12 types as afade)
- AC: Supports `overlap` toggle (default: enabled)
- AC: Two-input filter chain pattern
- AC: `.build()` returns `Filter` with correct acrossfade syntax

**FR-005**: Parameter validation rejects invalid values with helpful messages
- AC: Duration < 0 or > 60 returns PyValueError with descriptive message
- AC: Invalid transition type string returns PyValueError listing valid types
- AC: Invalid curve type returns PyValueError listing valid curves

## Non-Functional Requirements

**NFR-001**: All builders have PyO3 bindings with type stubs
- Metric: `scripts/verify_stubs.py` passes with all new types

**NFR-002**: Rust coverage for new transitions module >= 90%
- Metric: `cargo tarpaulin` shows >= 90% for `src/ffmpeg/transitions.rs`

**NFR-003**: PyO3 parity tests verify identical filter strings
- Metric: 3 parity tests pass (FadeBuilder, XfadeBuilder, AcrossfadeBuilder)

## Out of Scope

- Custom xfade expressions (the `custom` transition type with `expr` parameter)
- GPU-accelerated transitions
- Transition preview rendering

## Test Requirements

- ~24 Rust unit tests: FadeBuilder (~6), XfadeBuilder (~8), TransitionType (~3), AcrossfadeBuilder (~4), validation (~3)
- ~3 PyO3 parity tests: Python bindings produce identical filter strings

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `external-research.md`: FFmpeg fade, xfade (64 types), acrossfade parameters
- `evidence-log.md`: xfade duration range 0-60s, fade color values
- `codebase-patterns.md`: Two-input filter pattern, builder template