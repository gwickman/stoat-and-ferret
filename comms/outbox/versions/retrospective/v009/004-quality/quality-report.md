# Quality Report - v009

## Pre-Check: Python File Changes

```bash
git diff --name-only 7da9dcb HEAD -- '*.py'
```

Result: 13 Python files changed. Full quality gate run required.

## Quality Gate Run (Full)

### ruff

- **Status**: PASS
- **Return Code**: 0
- **Duration**: 0.07s
- **Output**:
```
All checks passed!
```

### mypy

- **Status**: PASS
- **Return Code**: 0
- **Duration**: 0.47s
- **Output**:
```
Success: no issues found in 49 source files
```

### pytest

- **Status**: PASS
- **Return Code**: 0
- **Duration**: 23.44s
- **Output** (summary):
```
platform win32 -- Python 3.13.11, pytest-9.0.2, pluggy-1.6.0
collected 956 items
...
956 passed
```

All 956 tests passed.

## Unconditional Test Categories

### Golden Scenarios

```bash
EXECUTION_BACKEND_MODE=replay uv run pytest tests/system/scenarios/ -v
```

- **Status**: N/A
- **Output**: `ERROR: file or directory not found: tests/system/scenarios/`
- **Note**: Directory does not exist yet in the project.

### Contract Tests

```bash
uv run pytest tests/contract/ -v
```

- **Status**: N/A
- **Output**: `ERROR: file or directory not found: tests/contract/`
- **Note**: Directory does not exist yet in the project.

### Parity Tests

```bash
uv run pytest tests/parity/ -v
```

- **Status**: N/A
- **Output**: `ERROR: file or directory not found: tests/parity/`
- **Note**: Directory does not exist yet in the project.

## Fixes Applied

None. No failures detected.

## Summary

- **Total Checks Run**: 3 (ruff, mypy, pytest)
- **All Passed**: Yes
- **Fix Rounds Required**: 0
- **Unconditional Categories**: 0/3 directories exist (all N/A)
- **Code Problems for Backlog**: None
- **Test Problems Fixed**: None
