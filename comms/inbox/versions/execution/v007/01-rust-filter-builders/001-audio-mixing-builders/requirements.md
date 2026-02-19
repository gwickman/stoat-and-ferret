# Requirements: audio-mixing-builders

## Goal

Build AmixBuilder, VolumeBuilder, AfadeBuilder, and DuckingPattern in Rust with PyO3 bindings, providing type-safe audio mixing filter generation for the effect workshop.

## Background

Backlog Item: BL-044

No Rust types exist for audio mixing, volume control, or audio fade effects. M2.4 requires amix for combining audio tracks, per-track volume control, fade in/out, and audio ducking patterns. The existing filter system handles video filters only. Without audio builders, mixing multiple audio sources requires manual FFmpeg filter string construction with no validation or ducking automation.

The v006 builder pattern (LRN-028) provides a proven template: `#[pyclass]` struct, `#[new]` constructor with validation, fluent `PyRefMut` chaining, `.build()` returning `Filter`, PyO3 bindings with `#[pyo3(name = "...")]`.

## Functional Requirements

**FR-001**: AmixBuilder supports configurable number of input tracks (range: 2-32)
- AC: `AmixBuilder::new(4)` creates a builder for 4-input mixing
- AC: Input count < 2 or > 32 returns `PyValueError`
- AC: Supports `duration` mode (`longest`, `shortest`, `first`)
- AC: Supports per-input `weights` as a list of floats
- AC: Supports `normalize` toggle (default: enabled)
- AC: `.build()` returns `Filter` with correct amix syntax

**FR-002**: VolumeBuilder validates range 0.0-10.0 using existing `validate_volume`
- AC: `VolumeBuilder::new(0.5)` creates a half-volume builder
- AC: Volume < 0.0 or > 10.0 returns `PyValueError`
- AC: Supports linear mode (float) and dB mode (string like "3dB")
- AC: Supports `precision` option (`fixed`, `float`, `double`)
- AC: `.build()` returns `Filter` with correct volume syntax

**FR-003**: AfadeBuilder supports configurable duration via expression engine
- AC: `AfadeBuilder::new("in", 3.0)` creates a 3-second fade-in
- AC: Supports `type` parameter: `in` or `out`
- AC: Supports `start_time` parameter in seconds
- AC: Supports all 12 curve types: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par (plus default tri)
- AC: Invalid curve type returns `PyValueError`
- AC: `.build()` returns `Filter` with correct afade syntax

**FR-004**: DuckingPattern lowers music volume during speech segments
- AC: DuckingPattern builds a FilterGraph (not a single FilterChain) using composition API
- AC: Uses `compose_branch` for asplit, `compose_chain` for sidechaincompress, `compose_merge` for amerge
- AC: Supports threshold (0.00097563-1.0, default: 0.125), ratio (1-20, default: 2), attack (0.01-2000ms, default: 20), release (0.01-9000ms, default: 250)
- AC: `.build()` returns a valid FilterGraph

**FR-005**: Edge case tests cover silence, clipping prevention, and format mismatches
- AC: Zero-volume input handled without error
- AC: Volume > 1.0 combined with amix normalize produces valid output
- AC: Fade duration longer than audio duration handled gracefully

## Non-Functional Requirements

**NFR-001**: All builders have PyO3 bindings exposed to Python with type stubs
- Metric: `scripts/verify_stubs.py` passes with all new types included

**NFR-002**: Rust coverage for new audio module >= 90%
- Metric: `cargo tarpaulin` shows >= 90% coverage for `src/ffmpeg/audio.rs`

**NFR-003**: PyO3 parity tests verify Python and Rust produce identical filter strings
- Metric: 4 parity tests pass (one per builder)

## Out of Scope

- Audio playback or rendering
- Real-time audio processing
- Audio format conversion
- Expression engine extensions (existing Expr API sufficient)

## Test Requirements

- ~30 Rust unit tests: AmixBuilder (~8), VolumeBuilder (~6), AfadeBuilder (~8), DuckingPattern (~5), edge cases (~3)
- ~4 PyO3 parity tests: Python builder calls produce identical filter strings to direct Rust calls
- DuckingPattern FilterGraph composition test (compose_branch + compose_chain + compose_merge integration)

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `external-research.md`: FFmpeg amix, volume, afade, sidechaincompress parameters
- `evidence-log.md`: Volume range 0.0-10.0, sidechaincompress parameter ranges
- `codebase-patterns.md`: Builder pattern template, two-input filter pattern