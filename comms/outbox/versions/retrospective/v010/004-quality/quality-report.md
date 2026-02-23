# Quality Report — v010

## Pre-check: Python File Changes

```
$ git diff --name-only 167dfe6 HEAD -- '*.py'
src/stoat_ferret/api/app.py
src/stoat_ferret/api/routers/health.py
src/stoat_ferret/api/routers/jobs.py
src/stoat_ferret/api/services/scan.py
src/stoat_ferret/ffmpeg/probe.py
src/stoat_ferret/jobs/queue.py
tests/test_api/test_jobs.py
tests/test_api/test_videos.py
tests/test_doubles/test_inmemory_job_queue.py
tests/test_event_loop_responsiveness.py
tests/test_ffprobe.py
tests/test_jobs/test_asyncio_queue.py
```

Result: **12 Python files changed** — full quality gates run required.

## Run 1: Full Quality Gates

### ruff

- **Status:** PASS
- **Return code:** 0
- **Duration:** 0.05s
- **Output:**
```
All checks passed!
```

### mypy

- **Status:** PASS
- **Return code:** 0
- **Duration:** 0.45s
- **Output:**
```
Success: no issues found in 49 source files
```

### pytest

- **Status:** PASS
- **Return code:** 0
- **Duration:** 21.1s
- **Tests collected:** 980
- **Output (summary):**
```
platform win32 -- Python 3.13.11, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\grant\Documents\projects\stoat-and-ferret
testpaths: tests
plugins: anyio-4.12.1, hypothesis-6.151.5, asyncio-1.3.0, cov-7.0.0
collected 980 items
... all passed ...
```

## Unconditional Test Categories

### Golden Scenarios (`tests/system/scenarios/`)

- **Status:** N/A — directory does not exist
- **Return code:** 4 (no tests collected)

### Contract Tests (`tests/contract/`)

- **Status:** N/A — directory does not exist
- **Return code:** 4 (no tests collected)

### Parity Tests (`tests/parity/`)

- **Status:** N/A — directory does not exist
- **Return code:** 4 (no tests collected)

## Fixes Applied

None — all checks passed on first run.

## Summary

All three quality gates (ruff, mypy, pytest) pass cleanly. 980 tests collected and all pass. No fixes were needed. The unconditional test category directories have not been created yet in this project, which is expected since those test infrastructure items are backlogged.
