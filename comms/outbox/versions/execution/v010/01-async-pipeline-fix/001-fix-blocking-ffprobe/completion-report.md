---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-fix-blocking-ffprobe

## Summary

Converted `ffprobe_video()` from blocking `subprocess.run()` to `asyncio.create_subprocess_exec()` so the asyncio event loop remains responsive during directory scans. Updated the sole caller `scan_directory()` to await the now-async function. Migrated all ffprobe and scan tests to use async-compatible mocks.

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | `ffprobe_video()` uses `asyncio.create_subprocess_exec()` with `communicate()` | PASS |
| FR-002 | 30-second timeout preserved via `asyncio.wait_for()` | PASS |
| FR-003 | All error paths preserved (FileNotFoundError, returncode, JSON parse, timeout with process kill) | PASS |
| FR-004 | `scan_directory()` awaits the now-async `ffprobe_video()` call | PASS |
| FR-005 | All tests migrated to async and pass with async-compatible mocks | PASS |

## Files Modified

| File | Change |
|------|--------|
| `src/stoat_ferret/ffmpeg/probe.py` | Converted `ffprobe_video()` to `async def`, replaced `subprocess.run()` with `asyncio.create_subprocess_exec()` + `asyncio.wait_for()`, added process kill on timeout |
| `src/stoat_ferret/api/services/scan.py` | Added `await` to `ffprobe_video()` call |
| `tests/test_ffprobe.py` | Converted contract and error test methods to `async def` with `await` |
| `tests/test_api/test_videos.py` | Updated `ffprobe_video` mocks to use `AsyncMock` via `new_callable`; converted sync `side_effect` to async |
| `tests/test_api/test_jobs.py` | Updated `ffprobe_video` mock to use `AsyncMock` via `new_callable` |

## Design Decisions

- Used `asyncio.TimeoutError` (not `builtins.TimeoutError`) for Python 3.10 compatibility per project memory and risk assessment
- On timeout, explicitly `proc.kill()` + `await proc.communicate()` to clean up the child process
- Used `new_callable=AsyncMock` in `patch()` calls rather than wrapping return values, for cleaner test code
- `test_websocket_broadcasts.py` unchanged as it patches `scan_directory` not `ffprobe_video`

## Test Results

- 936 passed, 20 skipped (skips are pre-existing: ffprobe/ffmpeg not available in test environment)
- All quality gates pass: ruff, ruff format, mypy
