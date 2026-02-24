# Implementation Plan: v001-bindings-trim

## Overview

Remove 5 unused v001 PyO3 bindings (find_gaps, merge_ranges, total_coverage, validate_crf, validate_speed) from the Rust-Python boundary. This involves removing PyO3 wrappers from Rust source, updating module registrations, cleaning up Python imports/stubs, removing parity tests and benchmarks, and documenting the changes.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `rust/stoat_ferret_core/src/timeline/range.rs` | Modify | Remove `#[pyfunction]` wrappers for find_gaps (lines ~549-554), merge_ranges (~567-571), total_coverage (~584-588) |
| `rust/stoat_ferret_core/src/sanitize/mod.rs` | Modify | Remove `#[pyfunction]` wrappers for validate_crf (~559-562), validate_speed (~579-582) |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Remove 5 functions from PyO3 module registration |
| `src/stoat_ferret_core/__init__.py` | Modify | Remove 5 imports, fallback stubs, `__all__` entries |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Regenerate and remove entries for 5 functions |
| `tests/test_pyo3_bindings.py` | Modify | Remove TestRangeListOperations class and TestSanitization crf/speed tests |
| `benchmarks/bench_ranges.py` | Delete | Remove entire file (3 benchmarks for removed bindings) |
| `docs/design/09-security-audit.md` | Modify | Note removal of validate_crf/validate_speed |
| `docs/design/10-performance-benchmarks.md` | Modify | Remove benchmark entries for range operations |
| `docs/CHANGELOG.md` | Modify | Add v012 removal entries with re-add triggers |

## Test Files

`tests/test_pyo3_bindings.py`

Post-removal: `uv run pytest && cd rust/stoat_ferret_core && cargo test`

## Implementation Stages

### Stage 1: Remove PyO3 wrappers from Rust

1. Read `rust/stoat_ferret_core/src/timeline/range.rs`
2. Remove `#[pyfunction]` wrappers for find_gaps, merge_ranges, total_coverage (preserve Rust-internal implementations)
3. Read `rust/stoat_ferret_core/src/sanitize/mod.rs`
4. Remove `#[pyfunction]` wrappers for validate_crf, validate_speed (preserve Rust-internal implementations)
5. Read `rust/stoat_ferret_core/src/lib.rs`
6. Remove 5 functions from PyO3 module registration

**Verification**: `cd rust/stoat_ferret_core && cargo clippy -- -D warnings && cargo test`

### Stage 2: Update Python imports and stubs

1. Read `src/stoat_ferret_core/__init__.py`
2. Remove 5 imports, fallback stubs, and `__all__` entries
3. Regenerate stubs: `cd rust/stoat_ferret_core && cargo run --bin stub_gen`
4. Read `stubs/stoat_ferret_core/_core.pyi`
5. Remove manual stub entries for 5 functions (find_gaps ~line 496, merge_ranges ~510, total_coverage ~524, validate_crf ~1734, validate_speed ~1748)
6. Verify stubs: `uv run python scripts/verify_stubs.py`
7. Post-removal grep: confirm removed function names return zero matches in manual stubs

**Verification**: `uv run mypy src/` and grep verification

### Stage 3: Remove parity tests and benchmarks

1. Read `tests/test_pyo3_bindings.py`
2. Remove `TestRangeListOperations` class (lines ~786-950, ~15 tests)
3. Remove TestSanitization crf/speed tests (~4 tests)
4. Update module-level export tests if they reference removed functions
5. Delete `benchmarks/bench_ranges.py`

**Verification**: `uv run pytest`

### Stage 4: Update documentation

1. Read and update `docs/design/09-security-audit.md` — note removal of validate_crf/validate_speed
2. Read and update `docs/design/10-performance-benchmarks.md` — remove range operations benchmark entries
3. Add v012 entries to `docs/CHANGELOG.md`:
   - Removed: find_gaps, merge_ranges, total_coverage PyO3 bindings (re-add trigger: Phase 3 Composition Engine)
   - Removed: validate_crf, validate_speed PyO3 bindings (re-add trigger: Python-level standalone validation need)

**Verification**: Manual review

## Test Infrastructure Updates

- Remove TestRangeListOperations class (~15 tests) from `tests/test_pyo3_bindings.py`
- Remove TestSanitization crf/speed tests (~4 tests) from `tests/test_pyo3_bindings.py`
- Update module-level export/import tests
- Remove `benchmarks/bench_ranges.py`

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings && cargo test
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
uv run python scripts/verify_stubs.py
```

## Risks

- Low risk — all 5 functions have zero production callers
- Stub regeneration gap: verify_stubs.py is one-way only; grep verification addresses this
- See `comms/outbox/versions/design/v012/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat(v012): remove 5 unused v001 PyO3 bindings

Remove find_gaps, merge_ranges, total_coverage from range.rs and
validate_crf, validate_speed from sanitize/mod.rs PyO3 wrappers.
Zero production callers. Rust-internal implementations preserved.
Re-add triggers documented in CHANGELOG.

Closes BL-067
```