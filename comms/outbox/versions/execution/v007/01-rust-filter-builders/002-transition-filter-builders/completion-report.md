---
status: complete
acceptance_passed: 30
acceptance_total: 30
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-transition-filter-builders

## Summary

Implemented transition filter builders in Rust with full PyO3 bindings: TransitionType enum (59 FFmpeg xfade variants), FadeBuilder (video fade in/out), XfadeBuilder (video crossfade), and AcrossfadeBuilder (audio crossfade). All builders follow the fluent pattern established by v006 audio builders and produce `Filter` objects compatible with FilterChain/FilterGraph.

## Acceptance Criteria

### FR-001: FadeBuilder (7/7)
- [x] `FadeBuilder("in", 3.0)` creates a 3-second fade-in
- [x] Supports `type`: `in` or `out`
- [x] Supports `duration` in seconds and `nb_frames` as alternative
- [x] Supports `color` parameter (named colors and hex #RRGGBB)
- [x] Supports `alpha` mode for alpha channel fading
- [x] Supports `start_time` parameter
- [x] `.build()` returns `Filter` with correct fade syntax

### FR-002: XfadeBuilder (7/7)
- [x] `XfadeBuilder(TransitionType.Wipeleft, 2.0, 5.0)` creates a wipe-left transition
- [x] TransitionType enum has all 59 FFmpeg xfade variants (actual FFmpeg count; requirement said 64 based on early research)
- [x] Duration validated in range 0.0-60.0 seconds
- [x] Offset parameter sets transition start relative to first input
- [x] Invalid transition type returns `ValueError`
- [x] Two-input filter chain pattern works
- [x] `.build()` returns `Filter` with correct xfade syntax

### FR-003: TransitionType enum (4/4)
- [x] All 59 FFmpeg xfade variants represented as enum variants
- [x] String conversion round-trip: `TransitionType.from_str("wipeleft") == TransitionType.Wipeleft`
- [x] Python binding exposes enum variants as class attributes
- [x] Invalid string returns appropriate error with valid types listed

### FR-004: AcrossfadeBuilder (6/6)
- [x] `AcrossfadeBuilder(2.0)` creates a 2-second audio crossfade
- [x] Supports `duration` in seconds
- [x] Supports `curve1` and `curve2` parameters (same types as afade)
- [x] Supports `overlap` toggle
- [x] Two-input filter chain pattern works
- [x] `.build()` returns `Filter` with correct acrossfade syntax

### FR-005: Parameter validation (3/3)
- [x] Duration validation returns ValueError with descriptive message
- [x] Invalid transition type string returns ValueError listing valid types
- [x] Invalid curve type returns ValueError listing valid curves

### NFR-001: PyO3 bindings with type stubs (1/1)
- [x] `scripts/verify_stubs.py` passes with all new types

### NFR-002: Rust test coverage (1/1)
- [x] 35 Rust unit tests covering all builders and validation paths

### NFR-003: PyO3 parity tests (1/1)
- [x] 46 Python parity tests pass (far exceeding ~3 minimum)

## Files Changed

### New Files
- `rust/stoat_ferret_core/src/ffmpeg/transitions.rs` - Rust implementation (1175 lines)
- `tests/test_transition_builders.py` - Python parity tests (46 tests)

### Modified Files
- `rust/stoat_ferret_core/src/ffmpeg/mod.rs` - Added `pub mod transitions;`
- `rust/stoat_ferret_core/src/lib.rs` - Registered 4 PyO3 classes
- `src/stoat_ferret_core/__init__.py` - Added imports, fallbacks, and __all__ entries
- `src/stoat_ferret_core/_core.pyi` - Added type stubs for all 4 new types
- `stubs/stoat_ferret_core/_core.pyi` - Added type stubs for all 4 new types

## Test Results

- Rust: 35 unit tests pass, clippy clean
- Python: 821 passed, 20 skipped (full suite)
- Ruff lint: pass
- Ruff format: pass
- Mypy: pass (on stoat_ferret_core)

## Notes

- The requirements specified "64 FFmpeg xfade variants" based on early research, but the actual FFmpeg source has 59 transition types (58 built-in + custom). All 59 are implemented.
- `pyo3_stub_gen`'s `#[gen_stub_pyclass]` macro does not support enums, so TransitionType was manually added to stub files.
- FadeCurve enum from the audio module is reused for AcrossfadeBuilder's curve parameters.
