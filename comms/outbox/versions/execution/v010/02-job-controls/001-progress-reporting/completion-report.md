---
status: complete
acceptance_passed: 9
acceptance_total: 9
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-progress-reporting

## Summary

Added progress tracking to the job queue and wired it through the scan handler to the API response. Users can now see real-time scan progress via the `progress` field in `GET /api/v1/jobs/{id}`.

## Changes

### Source Files

- **`src/stoat_ferret/jobs/queue.py`** — Added `progress: float | None = None` to `_AsyncJobEntry` dataclass and `JobResult`. Added `set_progress(job_id, value)` to `AsyncioJobQueue` and the `AsyncJobQueue` Protocol. Added no-op `set_progress()` to `InMemoryJobQueue`. Updated `get_result()` to include progress. Worker now injects `_job_id` into handler payload.
- **`src/stoat_ferret/api/services/scan.py`** — Added `progress_callback` keyword-only parameter to `scan_directory()`. Pre-collects video files for total count, calls callback with `processed / total_files` after each file. Added `queue` parameter to `make_scan_handler()` which builds a progress callback closure.
- **`src/stoat_ferret/api/routers/jobs.py`** — Wired `progress=result.progress` into `JobStatusResponse` construction.
- **`src/stoat_ferret/api/app.py`** — Passes `queue=job_queue` to `make_scan_handler()`.

### Test Files

- **`tests/test_jobs/test_asyncio_queue.py`** — 4 new tests: entry initializes with progress None, set_progress updates entry, set_progress with unknown job is no-op, progress preserved after completion.
- **`tests/test_doubles/test_inmemory_job_queue.py`** — 2 new tests: set_progress is no-op, set_progress with unknown job is no-op.
- **`tests/test_api/test_videos.py`** — 3 new tests: scan_directory calls progress callback, no callback no error, make_scan_handler wires progress to queue.
- **`tests/test_api/test_jobs.py`** — 2 new tests: response includes progress field, progress is None for completed empty scan.

## Acceptance Criteria

| # | Requirement | Status |
|---|-------------|--------|
| FR-001 | `_AsyncJobEntry` has `progress: float \| None = None` | Pass |
| FR-002 | `AsyncioJobQueue.set_progress()` updates entry progress | Pass |
| FR-003 | Protocol updated, `InMemoryJobQueue` has no-op `set_progress()` | Pass |
| FR-004 | Scan handler calls progress callback after each file | Pass |
| FR-005 | `GET /api/v1/jobs/{id}` includes populated progress field | Pass |
| NFR-001 | Progress value is 0.0-1.0 (scanned/total), None for queued | Pass |
| NFR-002 | No new `create_app()` kwargs | Pass |
| Test | All unit, API, and contract tests pass | Pass |
| Quality | ruff, mypy, pytest all pass | Pass |

## Design Decisions

1. **`_job_id` injection in payload**: The `process_jobs()` worker injects `_job_id` into the payload dict before calling the handler. This avoids changing the handler signature `(job_type, payload)` while giving handlers access to their job ID for progress reporting.

2. **Pre-collecting video files**: Changed `scan_directory()` from iterating with `root.glob()` directly to collecting video files into a list first. This provides the `total_files` count needed for accurate progress calculation (scanned/total).

3. **Optional `queue` parameter**: Added `queue` as an optional keyword argument to `make_scan_handler()` to maintain backward compatibility with all existing callers (tests, conftest fixtures).
