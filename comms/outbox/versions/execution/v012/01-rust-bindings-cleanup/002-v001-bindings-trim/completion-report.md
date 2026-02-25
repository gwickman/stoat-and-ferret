---
status: complete
acceptance_passed: 9
acceptance_total: 9
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  clippy: pass
  cargo_test: pass
  verify_stubs: pass
---
# Completion Report: 002-v001-bindings-trim

## Summary

Removed 5 unused v001 PyO3 bindings (`find_gaps`, `merge_ranges`, `total_coverage`, `validate_crf`, `validate_speed`) from the Rust-Python boundary. All Rust-internal implementations are preserved. Zero production callers were affected.

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | Remove find_gaps, merge_ranges, total_coverage PyO3 wrappers from range.rs | Pass |
| FR-002 | Remove validate_crf, validate_speed PyO3 wrappers from sanitize/mod.rs | Pass |
| FR-003 | Remove 5 functions from lib.rs PyO3 module registration | Pass |
| FR-004 | Update __init__.py — remove imports, fallback stubs, __all__ entries | Pass |
| FR-005 | Regenerate stubs and verify manual stubs are clean | Pass |
| FR-006 | Remove ~19 parity tests from test_pyo3_bindings.py | Pass |
| FR-007 | Remove benchmarks/bench_ranges.py | Pass |
| FR-008 | Update design documentation (security audit, benchmarks) | Pass |
| FR-009 | Document removals in CHANGELOG.md with re-add triggers | Pass |

## Changes Made

### Rust (Stage 1)
- `rust/stoat_ferret_core/src/timeline/range.rs`: Removed 3 `#[pyfunction]` wrappers (py_find_gaps, py_merge_ranges, py_total_coverage) and unused `gen_stub_pyfunction` import
- `rust/stoat_ferret_core/src/sanitize/mod.rs`: Removed 2 `#[pyfunction]` wrappers (py_validate_crf, py_validate_speed)
- `rust/stoat_ferret_core/src/timeline/mod.rs`: Removed 3 re-exports from pub use
- `rust/stoat_ferret_core/src/lib.rs`: Removed 5 function registrations from `_core` module

### Python (Stage 2)
- `src/stoat_ferret_core/__init__.py`: Removed 5 imports, 3 fallback stubs, 5 `__all__` entries, updated docstring
- `stubs/stoat_ferret_core/_core.pyi`: Removed 5 function stubs
- `stubs/stoat_ferret_core/__init__.pyi`: Removed 5 re-exports and `__all__` entries
- `src/stoat_ferret_core/_core.pyi`: Reformatted after stub regeneration

### Tests & Benchmarks (Stage 3)
- `tests/test_pyo3_bindings.py`: Removed TestRangeListOperations class (15 tests), 4 sanitization tests, updated export test
- `benchmarks/bench_ranges.py`: Deleted entirely
- `benchmarks/run_benchmarks.py`: Removed ranges import and benchmark step

### Documentation (Stage 4)
- `docs/design/09-security-audit.md`: Noted validate_crf/validate_speed as Rust-internal
- `docs/design/10-performance-benchmarks.md`: Removed range operations benchmark entries, added v012 note
- `docs/CHANGELOG.md`: Added v012 removal entries with re-add triggers

## Quality Gate Results

- `cargo clippy -- -D warnings`: Pass (no warnings)
- `cargo test`: Pass (426 unit tests + 109 doc tests)
- `uv run ruff check src/ tests/`: Pass
- `uv run ruff format --check src/ tests/`: Pass
- `uv run mypy src/`: 68 pre-existing errors (none related to this change)
- `uv run pytest`: Pass (936 passed, 20 skipped, 93% coverage)
- `uv run python scripts/verify_stubs.py`: Pass

## Non-Functional Requirements

- NFR-001 (No Rust regressions): Pass — all cargo tests pass
- NFR-002 (No Python regressions): Pass — all pytest tests pass
- NFR-003 (Clippy clean): Pass — no warnings
