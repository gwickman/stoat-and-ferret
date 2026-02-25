# v012 Quality Gates Report

All quality gates passed on the first run. No failures detected, no fixes required.

## Initial Results

| Check | Status | Return Code | Duration |
|-------|--------|-------------|----------|
| mypy | PASS | 0 | 0.45s |
| pytest | PASS | 0 | 16.88s |
| ruff | PASS | 0 | 0.06s |
| contract tests | PASS | 0 | 0.69s |
| parity tests | PASS | 0 | (included in contract) |
| golden scenarios | N/A | - | - |

## Python File Changes in v012

**Python files changed**: YES

Files modified since version start (310b036):
- `benchmarks/bench_ranges.py`
- `benchmarks/run_benchmarks.py`
- `src/stoat_ferret/ffmpeg/__init__.py`
- `src/stoat_ferret/ffmpeg/integration.py`
- `src/stoat_ferret_core/__init__.py`
- `tests/test_integration.py`
- `tests/test_pyo3_bindings.py`

## Failure Classification

No failures to classify.

| Test | File | Classification | Action | Backlog |
|------|------|----------------|--------|---------|
| (none) | - | - | - | - |

## Test Problem Fixes

No test problem fixes were required.

## Code Problem Deferrals

No code problems detected.

## Final Results

| Check | Status |
|-------|--------|
| mypy | PASS |
| pytest (923 tests) | PASS |
| ruff | PASS |
| contract tests (30 passed, 11 skipped) | PASS |
| parity tests | PASS |

## Outstanding Failures

None. All quality gates passed cleanly.

## Notes

- **Golden scenarios** (`tests/system/scenarios/`): Directory does not exist yet. No golden scenario tests to run.
- **Contract tests** (`tests/test_contract/`): 30 passed, 11 skipped. Includes parity tests (`test_repository_parity.py`, `test_search_parity.py`).
- **Parity tests**: Located within `tests/test_contract/` rather than a separate `tests/parity/` directory. All passed.
- Full pytest suite: 923 tests collected, all passed.
