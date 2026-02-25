# v012 Quality Report - Full Output

## Run Configuration

- **Project**: stoat-and-ferret
- **Version**: v012
- **Version start commit**: 310b036
- **Python files changed**: YES (7 files)
- **Date**: 2026-02-25

## Step 0: Python File Changes

```
git diff --name-only 310b036..HEAD -- '*.py'
```

Output:
```
benchmarks/bench_ranges.py
benchmarks/run_benchmarks.py
src/stoat_ferret/ffmpeg/__init__.py
src/stoat_ferret/ffmpeg/integration.py
src/stoat_ferret_core/__init__.py
tests/test_integration.py
tests/test_pyo3_bindings.py
```

Result: Python files changed, full quality gates required.

## Step 1: Quality Gates (run_quality_gates)

### mypy

- **Status**: PASS
- **Return code**: 0
- **Duration**: 0.45s
- **Output**:
```
Success: no issues found in 50 source files
```

### pytest

- **Status**: PASS
- **Return code**: 0
- **Duration**: 16.88s
- **Output** (summary):
```
platform win32 -- Python 3.13.11, pytest-9.0.2, pluggy-1.6.0
923 tests collected
923 passed
```

### ruff

- **Status**: PASS
- **Return code**: 0
- **Duration**: 0.06s
- **Output**:
```
All checks passed!
```

### Summary

Total duration: 17.4s. All 3 checks passed.

## Step 1b: Unconditional Test Categories

### Golden Scenarios

- **Directory**: `tests/system/scenarios/`
- **Status**: N/A (directory does not exist)
- **Notes**: No golden scenario tests have been created yet.

### Contract Tests

- **Directory**: `tests/test_contract/`
- **Command**: `uv run pytest tests/test_contract/ -v`
- **Status**: PASS
- **Results**: 30 passed, 11 skipped
- **Files**:
  - `test_ffmpeg_contract.py`
  - `test_repository_parity.py`
  - `test_search_parity.py`

### Parity Tests

- **Directory**: `tests/test_contract/` (no separate `tests/parity/` directory exists)
- **Status**: PASS (included in contract test run above)
- **Files**:
  - `test_repository_parity.py`
  - `test_search_parity.py`

## Step 2: Evaluation

All checks passed. No failures to evaluate.

## Step 3: Classification

No failures to classify. Steps 3a-3e are not applicable.

## Step 4: Final Gate Check

No fixes were applied, so no rerun was required. The initial run constitutes the final result.

## Fixes Applied

None. No diff to show.

## Before/After Comparison

Not applicable — no changes were made.
