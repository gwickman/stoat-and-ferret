# Quality Gate Full Report - v008

## Pre-Check: Python File Changes

```bash
git diff --name-only 7080c2e..603a16c -- '*.py'
```

Result: 13 Python files changed (6 source, 7 test). Full quality gates run required.

## Quality Gate Run: `run_quality_gates(project="stoat-and-ferret")`

### mypy

- **Status**: PASS
- **Return code**: 0
- **Duration**: 6.65s
- **Output**:
```
Success: no issues found in 49 source files
```

### ruff

- **Status**: PASS
- **Return code**: 0
- **Duration**: 0.08s
- **Output**:
```
All checks passed!
```

### pytest

- **Status**: PASS
- **Return code**: 0
- **Duration**: 24.96s
- **Output** (summary):
```
platform win32 -- Python 3.13.11, pytest-9.0.2, pluggy-1.6.0
collected 909 items
...
909 passed
```

All 909 tests passed across all test modules.

## Unconditional Test Categories

### Golden Scenarios (`tests/system/scenarios/`)

```
ERROR: file or directory not found: tests/system/scenarios/
collected 0 items
```

Directory does not exist. No golden scenario tests defined yet.

### Contract Tests (`tests/contract/`)

```
ERROR: file or directory not found: tests/contract/
collected 0 items
```

Directory does not exist. Contract tests are currently co-located in main test directory (e.g., `tests/test_async_repository_contract.py`, `tests/test_clip_repository_contract.py`, `tests/test_project_repository_contract.py`). These run as part of the main pytest suite.

### Parity Tests (`tests/parity/`)

```
ERROR: file or directory not found: tests/parity/
collected 0 items
```

Directory does not exist. Parity tests are currently in the main test directory (e.g., effect parity tests in `tests/test_api/test_effects.py`). These run as part of the main pytest suite.

## Fixes Applied

None. No fixes were needed.

## Before/After Comparison

Not applicable — all gates passed on the initial run.

## Summary

| Metric | Value |
|--------|-------|
| Total checks run | 3 (mypy, ruff, pytest) |
| Checks passed | 3/3 |
| Total tests collected | 909 |
| Tests passed | 909 |
| Tests failed | 0 |
| Fixes applied | 0 |
| Code problems identified | 0 |
| Re-runs needed | 0 |
