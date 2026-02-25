---
status: complete
acceptance_passed: 7
acceptance_total: 7
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  cargo_clippy: pass
  cargo_test: pass
---
# Completion Report: 003-v006-bindings-trim

## Summary

Removed 6 unused v006 PyO3 bindings from the Rust-Python boundary. The Expr (PyExpr) wrapper, validated_to_string, compose_chain, compose_branch, and compose_merge PyO3 wrappers were removed. All Rust-internal implementations are preserved — DrawtextBuilder and DuckingPattern continue to use native Rust calls.

## Acceptance Criteria

- [x] FR-001: Removed PyExpr wrapper from expression.rs; Rust-internal Expr enum and all 17 static methods preserved
- [x] FR-002: Removed validated_to_string, compose_chain, compose_branch, compose_merge PyO3 wrappers from filter.rs; Rust-internal FilterGraph methods preserved
- [x] FR-003: Removed PyExpr registration from lib.rs PyO3 module
- [x] FR-004: Removed Expr import, fallback stub, __all__ entry, and docstring section from __init__.py
- [x] FR-005: Updated stubs in both stubs/ and src/ directories; verify_stubs.py confirms clean API surface; grep for removed names returns zero matches
- [x] FR-006: Removed TestExpr class (16 tests) and TestFilterComposition class (15 tests) from test_pyo3_bindings.py; updated module-level export test
- [x] FR-007: Documented removals in docs/CHANGELOG.md with re-add triggers

## Non-Functional Requirements

- [x] NFR-001: cargo test passes (426 unit + 109 doc tests) — DrawtextBuilder and DuckingPattern tests work
- [x] NFR-002: uv run pytest passes (903 passed, 20 skipped, 93% coverage)
- [x] NFR-003: cargo clippy -- -D warnings passes clean

## Files Modified

| File | Change |
|------|--------|
| rust/stoat_ferret_core/src/ffmpeg/expression.rs | Removed PyExpr struct, #[pymethods] impl, pyo3 imports |
| rust/stoat_ferret_core/src/ffmpeg/filter.rs | Removed 4 PyO3 wrapper methods from FilterGraph |
| rust/stoat_ferret_core/src/lib.rs | Removed PyExpr from module registration |
| src/stoat_ferret_core/__init__.py | Removed Expr import, fallback stub, __all__ entry |
| src/stoat_ferret_core/_core.pyi | Removed Expr class and compose/validated_to_string methods |
| stubs/stoat_ferret_core/_core.pyi | Removed Expr class and compose/validated_to_string methods |
| tests/test_pyo3_bindings.py | Removed TestExpr and TestFilterComposition classes, updated export test |
| docs/CHANGELOG.md | Added v012 BL-068 removal entry with re-add triggers |

## Quality Gate Results

- ruff check: All checks passed
- ruff format: 119 files already formatted
- mypy: Success, no issues found in 50 source files
- pytest: 903 passed, 20 skipped, 93% coverage
- cargo clippy: Clean (no warnings)
- cargo test: 426 unit + 109 doc tests passed
- verify_stubs.py: All generated types present in manual stubs
