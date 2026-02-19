---
status: complete
acceptance_passed: 12
acceptance_total: 12
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  clippy: pass
  cargo_test: pass
---
# Completion Report: 001-audio-mixing-builders

## Summary

Implemented four audio mixing filter builders (VolumeBuilder, AfadeBuilder, AmixBuilder, DuckingPattern) as Rust PyO3 classes following the proven v006 builder template pattern. All builders support fluent method chaining, input validation, and produce correct FFmpeg filter strings.

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | AmixBuilder with inputs 2-32, duration mode, weights, normalize | PASS |
| FR-002 | VolumeBuilder with 0.0-10.0 range, linear/dB modes, precision | PASS |
| FR-003 | AfadeBuilder with in/out, duration, start_time, 11 curve types | PASS |
| FR-004 | DuckingPattern builds FilterGraph with asplit/sidechaincompress/anull | PASS |
| FR-005 | Edge case tests for silence, clipping prevention, format mismatches | PASS |
| NFR-001 | PyO3 bindings with type stubs | PASS |
| NFR-002 | Rust unit tests (54 tests in audio.rs) | PASS |
| NFR-003 | Python parity tests (42 tests in test_audio_builders.py) | PASS |
| QG-001 | ruff check passes | PASS |
| QG-002 | ruff format passes | PASS |
| QG-003 | mypy passes | PASS |
| QG-004 | pytest passes (775 passed, 92.71% coverage) | PASS |

## Files Created

- `rust/stoat_ferret_core/src/ffmpeg/audio.rs` - All four builders with FadeCurve enum and 54 Rust unit tests
- `tests/test_audio_builders.py` - 42 Python parity tests

## Files Modified

- `rust/stoat_ferret_core/src/ffmpeg/mod.rs` - Added `pub mod audio;`
- `rust/stoat_ferret_core/src/lib.rs` - Registered 4 PyO3 classes
- `src/stoat_ferret_core/__init__.py` - Added imports, fallback stubs, __all__ entries
- `src/stoat_ferret_core/_core.pyi` - Added type stubs for 4 new classes
- `stubs/stoat_ferret_core/_core.pyi` - Added type stubs for 4 new classes

## Notes

- DuckingPattern uses `compose_branch` (asplit), `compose_merge` (sidechaincompress), and `compose_chain` (anull passthrough) from FilterGraph's composition API
- FadeCurve enum has 11 variants matching FFmpeg's afade curve options
- VolumeBuilder supports both linear (float) and dB (string) modes via separate constructors
