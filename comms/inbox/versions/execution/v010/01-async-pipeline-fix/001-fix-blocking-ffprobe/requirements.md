# Requirements: fix-blocking-ffprobe

## Goal

Convert `ffprobe_video()` from blocking `subprocess.run()` to `asyncio.create_subprocess_exec()` so the asyncio event loop remains responsive during scans.

## Background

Backlog Item: BL-072

The `ffprobe_video()` function in `src/stoat_ferret/ffmpeg/probe.py` uses synchronous `subprocess.run()` with a 30-second timeout per file. When called from the async scan handler, this blocks the entire asyncio event loop for each ffprobe call. While blocked, the server cannot handle HTTP requests — including job status polling — making the scan appear frozen. This is the primary cause of the "scan directory hangs forever" bug.

## Functional Requirements

**FR-001: Async ffprobe execution**
- `ffprobe_video()` must use `asyncio.create_subprocess_exec()` with `communicate()` instead of `subprocess.run()`
- Function signature changes from `def ffprobe_video(...)` to `async def ffprobe_video(...)`
- Acceptance: ffprobe_video() returns correct VideoMetadata with mocked asyncio.create_subprocess_exec

**FR-002: Timeout preservation**
- Preserve the existing 30-second timeout using `asyncio.wait_for(proc.communicate(), timeout=30)`
- Acceptance: asyncio.wait_for() fires reliably at 30s threshold in tests

**FR-003: Error handling preservation**
- All existing error paths preserved: FileNotFoundError, non-zero returncode, JSON parse errors, empty stdout, stderr content, process killed
- Acceptance: all existing error-handling test cases pass with async implementation

**FR-004: Caller update**
- `scan_directory()` in `src/stoat_ferret/api/services/scan.py` must `await` the now-async `ffprobe_video()` call
- Acceptance: scan of a directory with multiple video files completes without blocking other API requests

**FR-005: Test migration**
- All tests in `tests/test_ffprobe.py` must become `async def` and mock `asyncio.create_subprocess_exec` instead of `subprocess.run`
- Scan-related tests in `tests/test_api/test_videos.py`, `tests/test_api/test_jobs.py`, and `tests/test_api/test_websocket_broadcasts.py` must use async-compatible ffprobe mocks where they reference ffprobe_video
- Acceptance: all existing ffprobe and scan tests pass with the async implementation

## Non-Functional Requirements

**NFR-001: Event loop responsiveness**
- HTTP status polling endpoint must remain responsive during an active scan job
- Metric: GET /api/v1/jobs/{id} responds within 2 seconds during scan (validated by BL-078)

**NFR-002: Python 3.10 compatibility**
- `asyncio.create_subprocess_exec()` is available in Python 3.10+ and requires `ProactorEventLoop` on Windows (the default since Python 3.8)

## Handler Pattern

Not applicable for v010 — no new handlers introduced.

## Out of Scope

- Converting `executor.py:96` blocking `subprocess.run()` — not in async context, future tech debt
- Converting `health.py:96` — handled by BL-077 (feature 002-async-blocking-ci-gate)
- Adding progress or cancellation callbacks — handled by BL-073 and BL-074

## Test Requirements

- Unit: async ffprobe_video() returns correct VideoMetadata with mocked asyncio.create_subprocess_exec
- Unit: timeout behavior — asyncio.wait_for() fires at 30s threshold
- Unit: error handling — FileNotFoundError, non-zero returncode, JSON parse errors, empty stdout, stderr, process killed
- Existing: tests/test_ffprobe.py migrated to async
- Existing: tests/test_api/test_videos.py, test_jobs.py, test_websocket_broadcasts.py ffprobe mocks updated to async where applicable

## Reference

See `comms/outbox/versions/design/v010/004-research/` for supporting evidence.