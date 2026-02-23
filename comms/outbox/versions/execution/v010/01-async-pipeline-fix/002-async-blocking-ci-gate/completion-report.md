---
status: complete
acceptance_passed: 3
acceptance_total: 3
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-async-blocking-ci-gate

## Summary

Enabled ruff ASYNC rules (ASYNC221, ASYNC210, ASYNC230) to detect blocking calls in async functions at CI time, and converted `_check_ffmpeg()` in health.py from sync to async using `asyncio.to_thread()`.

## Changes Made

### pyproject.toml
- Added `"ASYNC"` to the ruff lint `select` list, enabling ASYNC221 (blocking subprocess), ASYNC210 (blocking HTTP), and ASYNC230 (blocking file I/O) rules.

### src/stoat_ferret/api/routers/health.py
- Added `import asyncio`
- Converted `_check_ffmpeg()` from `def` to `async def`
- Wrapped `subprocess.run()` call with `asyncio.to_thread()` to avoid blocking the event loop
- Updated caller in `readiness()` to `await _check_ffmpeg()`

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001 | ruff ASYNC rules enabled in pyproject.toml | PASS |
| FR-002 | health.py _check_ffmpeg() uses asyncio.to_thread() | PASS |
| FR-003 | `uv run ruff check src/ tests/` passes with zero ASYNC violations | PASS |

## Quality Gates

| Gate | Result |
|------|--------|
| ruff check | pass (0 violations) |
| ruff format | pass (117 files already formatted) |
| mypy | pass (49 source files, no issues) |
| pytest | pass (936 passed, 20 skipped, 92.81% coverage) |
