---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  clippy: pass
  cargo_test: pass
---
# Completion Report: 002-speed-builders

## Summary

Implemented type-safe speed control builders for FFmpeg video and audio speed adjustment in `rust/stoat_ferret_core/src/ffmpeg/speed.rs`. The `SpeedControl` struct provides `setpts` filter generation for video speed and `atempo` filter generation for audio speed with automatic chaining for values outside the [0.5, 2.0] quality range.

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | Video speed adjustable via setpts with factor range 0.25x-4.0x | PASS |
| FR-002 | Audio speed via atempo with automatic chaining for factors above 2.0x | PASS |
| FR-003 | Option to drop audio entirely instead of speed-adjusting it | PASS |
| FR-004 | Validation rejects out-of-range values with helpful error messages | PASS |
| FR-005 | Unit tests cover edge cases: 1x (no-op), boundary values, extreme speeds | PASS |

## Implementation Details

### Files Created
- `rust/stoat_ferret_core/src/ffmpeg/speed.rs` - Core implementation with Rust API, PyO3 bindings, and 41 unit tests + 4 doc tests + 4 proptests

### Files Modified
- `rust/stoat_ferret_core/src/ffmpeg/mod.rs` - Added `pub mod speed;`
- `rust/stoat_ferret_core/src/lib.rs` - Registered `SpeedControl` PyO3 class
- `src/stoat_ferret_core/__init__.py` - Added `SpeedControl` import, fallback stub, `__all__` entry
- `src/stoat_ferret_core/_core.pyi` - Auto-regenerated stubs
- `stubs/stoat_ferret_core/_core.pyi` - Added manual `SpeedControl` type stub
- `tests/test_pyo3_bindings.py` - Added `TestSpeedControl` class (24 tests) and module exports check
- `tests/test_coverage/test_import_fallback.py` - Added `DrawtextBuilder` and `SpeedControl` to fallback stub tests

### Key Design Decisions

1. **Positional filter syntax**: Used `Filter::new(format!("setpts={expr}"))` instead of `Filter::new("setpts").param(...)` because FFmpeg expects positional syntax (`setpts=0.5*PTS` not `setpts=expr=0.5*PTS`).

2. **Reused existing validation**: Leveraged `sanitize::validate_speed()` for the [0.25, 4.0] range check rather than duplicating validation logic.

3. **Atempo chaining algorithm**: For speeds > 2.0, decompose using stages of 2.0 plus remainder. For speeds < 0.5, decompose using stages of 0.5 plus remainder. Each chained value stays within the [0.5, 2.0] quality range.

4. **Clean number formatting**: Implemented `format_pts_multiplier()` and `format_tempo_value()` helpers to produce clean output like `0.5*PTS` instead of `0.500000*PTS`.

## Quality Gate Results

| Gate | Result | Notes |
|------|--------|-------|
| ruff check | PASS | No errors in src/ or tests/ |
| ruff format | PASS | All files formatted |
| mypy | PASS | 11 pre-existing errors only, no new errors |
| cargo clippy | PASS | Zero warnings |
| cargo test | PASS | 41 unit + 4 doc tests + 4 proptests |
| pytest | PASS | 708 passed, 20 skipped, 0 failed |

## Test Coverage

- **Rust unit tests**: 41 tests covering construction, validation, setpts formula, atempo chaining, drop audio, edge cases, filter chain integration
- **Rust proptests**: 4 property-based tests for range validation, chain value bounds, chain product correctness, and setpts validity
- **Rust doc tests**: 4 documentation examples as tests
- **Python tests**: 24 PyO3 binding tests covering construction, validation, filter output, chaining, drop audio, type checks, repr, and filter chain integration
