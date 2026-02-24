# Test Strategy — v012 API Surface & Bindings Cleanup

## Theme 01: rust-bindings-cleanup

### Feature 001-execute-command-removal

| Category | Requirement | Details |
|----------|-------------|---------|
| **Unit tests** | Remove `tests/test_integration.py` | All 13 test methods (8 execute_command + 5 CommandExecutionError) test only the removed function. Entire file deletion. |
| **Unit tests** | Verify no import breakage | Run full `uv run pytest` after removal to confirm no other test imports execute_command or CommandExecutionError. |
| **System/Golden** | Not applicable | execute_command has no production execution flow — nothing to regression-test. |
| **Parity tests** | Not applicable | execute_command is Python-only, no parity dimension. |
| **Contract tests** | Not applicable | No DTO changes. |
| **Replay fixtures** | Not applicable | No execution patterns affected. |

**Post-removal verification**:
- `uv run pytest` — all remaining tests pass
- `uv run ruff check src/` — no unused imports
- `uv run mypy src/` — no type errors from removed exports

### Feature 002-v001-bindings-trim

| Category | Requirement | Details |
|----------|-------------|---------|
| **Unit tests** | Remove 15 tests in TestRangeListOperations | `test_pyo3_bindings.py:786-950` — tests for find_gaps, merge_ranges, total_coverage |
| **Unit tests** | Remove 4 tests in TestSanitization | CRF and speed validation tests for the PyO3 wrappers |
| **Unit tests** | Update module-level export tests | Any test asserting __all__ contents or import availability for removed functions |
| **Benchmarks** | Remove `benchmarks/bench_ranges.py` | 3 benchmarks (merge_ranges ×2, find_gaps ×1) reference removed bindings |
| **System/Golden** | Not applicable | Removed functions had zero production callers. |
| **Parity tests** | Removed with bindings | Parity tests for these bindings become invalid — they tested Python-Rust equivalence for functions no longer exposed to Python. |
| **Contract tests** | Not applicable | No DTO changes. |

**Post-removal verification**:
- `cargo test` in `rust/stoat_ferret_core/` — Rust-internal functions (TimeRange ops, validate_crf, validate_speed) still work
- `cargo clippy -- -D warnings` — no dead code warnings from removing PyO3 wrappers
- `uv run pytest` — all remaining Python tests pass
- Stub verification: `uv run python scripts/verify_stubs.py` — stubs match reduced API

### Feature 003-v006-bindings-trim

| Category | Requirement | Details |
|----------|-------------|---------|
| **Unit tests** | Remove 16 tests in TestExpr | `test_pyo3_bindings.py:1006-1140` — Expr static methods and operators |
| **Unit tests** | Remove ~15 composition tests | `test_pyo3_bindings.py:362-505` — compose_chain, compose_branch, compose_merge, validated_to_string |
| **Unit tests** | Update module-level export tests | Any test asserting __all__ contents or import availability for removed bindings |
| **System/Golden** | Not applicable | Removed bindings had zero production callers. |
| **Parity tests** | Removed with bindings | Parity tests for Expr and composition bindings become invalid. |
| **Contract tests** | Not applicable | No DTO changes. |

**Post-removal verification**:
- `cargo test` — DrawtextBuilder (uses Expr internally) and DuckingPattern (uses compose internally) still pass
- `cargo clippy -- -D warnings` — no warnings
- `uv run pytest` — all remaining Python tests pass
- Stub verification: `uv run python scripts/verify_stubs.py`

## Theme 02: workshop-and-docs-polish

### Feature 001-transition-gui

| Category | Requirement | Details |
|----------|-------------|---------|
| **Unit tests** | useTransitionStore tests (Vitest) | Test source/target clip selection, reset, isReady computed state |
| **Unit tests** | ClipPairSelector component tests (Vitest) | Test rendering clip pairs, selection callbacks, visual state for selected/unselected |
| **Unit tests** | TransitionPanel component tests (Vitest) | Test transition type selection, parameter form rendering, submit flow |
| **System/Golden** | End-to-end transition flow | User selects two adjacent clips → chooses transition → configures params → applies → transition stored. Test should verify the full GUI flow calls the correct API endpoint. |
| **Parity tests** | Not applicable | No Rust-Python parity dimension — this is frontend-only. |
| **Contract tests** | Not applicable | TransitionRequest/TransitionResponse DTOs already exist and are tested. |
| **Replay fixtures** | Not applicable | No new backend execution patterns. |

**New test files**:
- `gui/src/stores/__tests__/transitionStore.test.ts`
- `gui/src/components/__tests__/ClipPairSelector.test.tsx`
- `gui/src/components/__tests__/TransitionPanel.test.tsx`

**Verification**:
- `npx vitest run` in `gui/` — all new and existing frontend tests pass
- `npx tsc -b` — no TypeScript errors

### Feature 002-api-spec-corrections

| Category | Requirement | Details |
|----------|-------------|---------|
| **Unit tests** | Not applicable | Documentation-only change — no code to test. |
| **System/Golden** | Not applicable | No execution flow changes. |
| **Parity tests** | Not applicable | No binding changes. |
| **Contract tests** | Not applicable | No DTO changes. |
| **Replay fixtures** | Not applicable | No execution patterns. |

**Verification**:
- Manual review: all job status examples in `05-api-specification.md` show realistic values
- Manual review: `03_api-reference.md` progress description says "0.0-1.0"
- Manual review: status enum includes "cancelled"

## Summary

| Feature | Tests Removed | Tests Created | Tests Updated | Verification |
|---------|--------------|---------------|---------------|-------------|
| 001-execute-command-removal | 13 (entire file) | 0 | 0 | pytest, ruff, mypy |
| 002-v001-bindings-trim | ~22 | 0 | Export tests | cargo test, pytest, verify_stubs |
| 003-v006-bindings-trim | ~31 | 0 | Export tests | cargo test, pytest, verify_stubs |
| 001-transition-gui | 0 | ~3 test files | 0 | vitest, tsc |
| 002-api-spec-corrections | 0 | 0 | 0 | Manual review |

**Net test change**: ~66 tests removed (dead code parity tests), ~3 new test files created (transition GUI). Overall test count decreases as expected for a cleanup version.
