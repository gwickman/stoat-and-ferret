# Implementation Plan: v006-bindings-trim

## Overview

Remove 6 unused v006 PyO3 bindings (Expr/PyExpr, validated_to_string, compose_chain, compose_branch, compose_merge) from the Rust-Python boundary. The Rust-internal implementations remain intact for DrawtextBuilder and DuckingPattern usage. This involves removing PyO3 wrappers, updating module registrations, cleaning up Python imports/stubs, and removing ~31 parity tests.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `rust/stoat_ferret_core/src/ffmpeg/expression.rs` | Modify | Remove PyExpr wrapper (~lines 537-542) |
| `rust/stoat_ferret_core/src/ffmpeg/filter.rs` | Modify | Remove validated_to_string (~984-989), compose_chain (~1006-1012), compose_branch (~1031-1038), compose_merge (~1056-1063) PyO3 wrappers |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Remove 6 bindings from PyO3 module registration |
| `src/stoat_ferret_core/__init__.py` | Modify | Remove 6+ imports, fallback stubs, `__all__` entries |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Regenerate and remove ~157 lines for Expr class + FilterGraph compose methods |
| `tests/test_pyo3_bindings.py` | Modify | Remove TestExpr class and composition tests (~31 tests) |
| `docs/CHANGELOG.md` | Modify | Add v012 removal entries with re-add triggers |

## Test Files

`tests/test_pyo3_bindings.py`

Post-removal: `uv run pytest && cd rust/stoat_ferret_core && cargo test`

## Implementation Stages

### Stage 1: Remove PyO3 wrappers from Rust

1. Read `rust/stoat_ferret_core/src/ffmpeg/expression.rs`
2. Remove PyExpr wrapper (PyO3 bindings at ~line 537-542) — preserve the Rust-internal Expr enum
3. Read `rust/stoat_ferret_core/src/ffmpeg/filter.rs`
4. Remove `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge` PyO3 wrappers — preserve Rust-internal FilterGraph methods
5. Read `rust/stoat_ferret_core/src/lib.rs`
6. Remove 6 bindings from PyO3 module registration

**Verification**: `cd rust/stoat_ferret_core && cargo clippy -- -D warnings && cargo test`

### Stage 2: Update Python imports and stubs

1. Read `src/stoat_ferret_core/__init__.py`
2. Remove imports for Expr, validated_to_string, compose_chain, compose_branch, compose_merge
3. Remove fallback stubs and `__all__` entries
4. Regenerate stubs: `cd rust/stoat_ferret_core && cargo run --bin stub_gen`
5. Read `stubs/stoat_ferret_core/_core.pyi`
6. Remove manual stub entries for Expr class (~lines 1464-1621) and FilterGraph compose methods (~lines 1369-1450)
7. Verify stubs: `uv run python scripts/verify_stubs.py`
8. Post-removal grep: confirm removed names (Expr, validated_to_string, compose_chain, compose_branch, compose_merge) return zero matches in manual stubs

**Verification**: `uv run mypy src/` and grep verification

### Stage 3: Remove parity tests

1. Read `tests/test_pyo3_bindings.py`
2. Remove `TestExpr` class (~lines 1006-1140, ~16 tests)
3. Remove composition tests (~lines 362-505, ~15 tests)
4. Update module-level export tests if they reference removed bindings

**Verification**: `uv run pytest`

### Stage 4: Document removal

1. Add v012 entries to `docs/CHANGELOG.md`:
   - Removed: Expr (PyExpr) PyO3 binding (re-add trigger: Python-level expression building for custom filter effects)
   - Removed: validated_to_string, compose_chain, compose_branch, compose_merge PyO3 bindings (re-add trigger: Python-level filter graph composition outside Rust builders)

**Verification**: Manual review

## Test Infrastructure Updates

- Remove TestExpr class (~16 tests) from `tests/test_pyo3_bindings.py`
- Remove composition tests (~15 tests) from `tests/test_pyo3_bindings.py`
- Update module-level export/import tests

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

- Low risk — all 6 bindings have zero production callers
- Rust-internal usage (DrawtextBuilder, DuckingPattern) uses native Rust, not PyO3 wrappers
- If Expr class deletion block is too large for Edit, use Write tool to rewrite the file
- See `comms/outbox/versions/design/v012/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat(v012): remove 6 unused v006 PyO3 bindings

Remove Expr (PyExpr), validated_to_string, compose_chain,
compose_branch, compose_merge from PyO3 wrappers. Zero production
callers. Rust-internal usage (DrawtextBuilder, DuckingPattern)
unaffected. Re-add triggers documented in CHANGELOG.

Closes BL-068
```
