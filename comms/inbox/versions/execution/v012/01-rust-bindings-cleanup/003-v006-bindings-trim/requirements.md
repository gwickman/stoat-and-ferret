# Feature: v006-bindings-trim

## Goal

Remove 6 unused v006 PyO3 bindings that have zero production callers and are only exercised in parity tests.

## Background

Three v006 filter engine features (Expression Engine, Graph Validation, Filter Composition) expose Python bindings via PyO3 that are only used in parity tests, never in production code. The Rust code uses these capabilities internally — DrawtextBuilder uses Expr for alpha fade expressions at `ffmpeg/drawtext.rs:319-356`, and DuckingPattern uses composition at `ffmpeg/audio.rs:720-745`. These internal usages work via native Rust calls, not PyO3 wrappers.

Backlog Item: BL-068

## Functional Requirements

**FR-001**: Remove `Expr` (PyExpr) PyO3 wrapper from `rust/stoat_ferret_core/src/ffmpeg/expression.rs`
- Acceptance: PyExpr wrapper removed; Rust-internal Expr enum and all 17 static methods preserved

**FR-002**: Remove `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge` PyO3 wrappers from `rust/stoat_ferret_core/src/ffmpeg/filter.rs`
- Acceptance: `#[pyfunction]`/`#[pymethods]` wrappers removed; Rust-internal FilterGraph methods preserved

**FR-003**: Remove all 6 bindings from `rust/stoat_ferret_core/src/lib.rs` PyO3 module registration
- Acceptance: Bindings no longer registered in the Python module

**FR-004**: Update `src/stoat_ferret_core/__init__.py` — remove 6+ imports, fallback stubs, and `__all__` entries
- Acceptance: Module no longer imports or exports these bindings

**FR-005**: Regenerate `stubs/stoat_ferret_core/_core.pyi` and verify manual stubs are clean
- Acceptance: Stub file reflects reduced API surface (~157 lines removed for Expr class + FilterGraph compose methods); grep for removed names returns zero matches

**FR-006**: Remove ~31 parity tests from `tests/test_pyo3_bindings.py`
- Acceptance: TestExpr class (~16 tests) and composition tests (~15 tests) removed

**FR-007**: Document removals in `docs/CHANGELOG.md` with re-add triggers
- Acceptance: Expr: Python-level expression building; compose: Python-level filter graph composition

## Non-Functional Requirements

**NFR-001**: No Rust-internal regressions
- Metric: `cargo test` passes — DrawtextBuilder and DuckingPattern tests continue to work

**NFR-002**: No Python test regressions
- Metric: All remaining Python tests pass (`uv run pytest` exits 0)

**NFR-003**: Clippy clean
- Metric: `cargo clippy -- -D warnings` passes

## Handler Pattern

Not applicable for v012 — no new handlers introduced.

## Out of Scope

- Modifying Rust-internal usage (DrawtextBuilder, DuckingPattern)
- Adding reverse-verification to verify_stubs.py
- C4 documentation updates (tracked as BL-069)

## Test Requirements

- Remove TestExpr class from `tests/test_pyo3_bindings.py` (~16 tests)
- Remove composition tests from `tests/test_pyo3_bindings.py` (~15 tests)
- Update module-level export tests to reflect removed bindings
- Post-removal: `cargo test`, `cargo clippy -- -D warnings`, `uv run pytest`, `uv run python scripts/verify_stubs.py`

## Reference

See `comms/outbox/versions/design/v012/004-research/` for supporting evidence.