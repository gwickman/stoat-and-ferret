# Feature: v001-bindings-trim

## Goal

Remove 5 unused v001 PyO3 bindings that have zero production callers.

## Background

Several Rust functions were exposed via PyO3 in v001 "just in case" but have never been called from Python production code. TimeRange list operations (find_gaps, merge_ranges, total_coverage) were design-ahead code for future timeline editing. Input sanitization functions (validate_crf, validate_speed) overlap with Rust-internal validation in FFmpegCommand.build() and SpeedControl.new(). All 5 functions remain available as Rust-internal implementations.

Backlog Item: BL-067

## Functional Requirements

**FR-001**: Remove `find_gaps`, `merge_ranges`, `total_coverage` PyO3 wrappers from `rust/stoat_ferret_core/src/timeline/range.rs`
- Acceptance: `#[pyfunction]` wrappers removed; Rust-internal implementations preserved

**FR-002**: Remove `validate_crf`, `validate_speed` PyO3 wrappers from `rust/stoat_ferret_core/src/sanitize/mod.rs`
- Acceptance: `#[pyfunction]` wrappers removed; Rust-internal implementations preserved

**FR-003**: Remove all 5 functions from `rust/stoat_ferret_core/src/lib.rs` PyO3 module registration
- Acceptance: Functions no longer registered in the Python module

**FR-004**: Update `src/stoat_ferret_core/__init__.py` — remove 5 imports, fallback stubs, and `__all__` entries
- Acceptance: Module no longer imports or exports these 5 functions

**FR-005**: Regenerate `stubs/stoat_ferret_core/_core.pyi` and verify manual stubs are clean
- Acceptance: Stub file reflects reduced API surface; grep for removed function names returns zero matches in manual stubs

**FR-006**: Remove ~22 parity tests from `tests/test_pyo3_bindings.py`
- Acceptance: TestRangeListOperations class (~15 tests) and TestSanitization crf/speed tests (~4 tests) removed

**FR-007**: Remove `benchmarks/bench_ranges.py`
- Acceptance: File deleted (3 benchmarks reference removed bindings)

**FR-008**: Update design documentation
- Acceptance: `docs/design/09-security-audit.md` notes removal of validate_crf/validate_speed; `docs/design/10-performance-benchmarks.md` removes benchmark entries

**FR-009**: Document removals in `docs/CHANGELOG.md` with re-add triggers
- Acceptance: TimeRange ops: Phase 3 Composition Engine; sanitization: Python-level standalone validation need

## Non-Functional Requirements

**NFR-001**: No Rust-internal regressions
- Metric: `cargo test` passes in `rust/stoat_ferret_core/`

**NFR-002**: No Python test regressions
- Metric: All remaining Python tests pass (`uv run pytest` exits 0)

**NFR-003**: Clippy clean
- Metric: `cargo clippy -- -D warnings` passes with no dead code warnings

## Handler Pattern

Not applicable for v012 — no new handlers introduced.

## Out of Scope

- Modifying Rust-internal usage of these functions
- Adding reverse-verification to verify_stubs.py (separate backlog concern)
- C4 documentation updates (tracked as BL-069)

## Test Requirements

- Remove TestRangeListOperations class from `tests/test_pyo3_bindings.py` (~15 tests)
- Remove TestSanitization crf/speed tests from `tests/test_pyo3_bindings.py` (~4 tests)
- Update module-level export tests to reflect removed bindings
- Remove `benchmarks/bench_ranges.py`
- Post-removal: `cargo test`, `cargo clippy -- -D warnings`, `uv run pytest`, `uv run python scripts/verify_stubs.py`

## Reference

See `comms/outbox/versions/design/v012/004-research/` for supporting evidence.