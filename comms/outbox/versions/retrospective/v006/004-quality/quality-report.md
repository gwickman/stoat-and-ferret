# Quality Gate Report — v006

## Run Summary

- **Project**: stoat-and-ferret
- **Version**: v006
- **Date**: 2026-02-19
- **Overall**: ALL PASSED
- **Total duration**: 15.93s

## Check: mypy

- **Status**: PASSED
- **Return code**: 0
- **Duration**: 4.73s

```
Success: no issues found in 49 source files
```

## Check: pytest

- **Status**: PASSED
- **Return code**: 0
- **Duration**: 11.14s

```
============================= test session starts =============================
platform win32 -- Python 3.13.11, pytest-9.0.2, pluggy-1.6.0
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: C:\Users\grant\Documents\projects\stoat-and-ferret
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.12.1, hypothesis-6.151.5, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.AUTO, debug=False
collected 753 items

... 753 passed ...
```

Key statistics:
- 753 tests collected
- 753 tests passed
- 0 failures
- 0 errors
- 0 skipped

## Check: ruff

- **Status**: PASSED
- **Return code**: 0
- **Duration**: 0.05s

```
All checks passed!
```

## Fixes Applied

No fixes were required. All gates passed on the initial run.

## Before/After Comparison

Not applicable — no changes were made.
