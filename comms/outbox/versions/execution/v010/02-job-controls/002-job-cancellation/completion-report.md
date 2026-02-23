---
status: complete
acceptance_passed: 16
acceptance_total: 16
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  vitest: pass
---
# Completion Report: 002-job-cancellation

## Summary

Implemented cooperative job cancellation with a cancel endpoint and partial results. Users can now stop long-running scans via the REST API and frontend cancel button.

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001 | cancel_event on _AsyncJobEntry | PASS |
| FR-002 | AsyncioJobQueue.cancel() sets cancel event | PASS |
| FR-003 | Protocol update + InMemoryJobQueue no-op cancel | PASS |
| FR-004 | CANCELLED job status enum | PASS |
| FR-005 | Scan handler cancellation checkpoint | PASS |
| FR-006 | Cancel REST endpoint (200/404/409) | PASS |
| FR-007 | Frontend cancel button | PASS |
| NFR-001 | Python 3.10 compatibility | PASS |
| NFR-002 | No new DI surface | PASS |

## Test Coverage

- **Unit tests**: cancel_event initialization, cancel() sets event, cancel() with invalid job_id raises KeyError, CANCELLED status serialization, cancelled job has CANCELLED status with partial results
- **API tests**: POST /cancel returns 404 for unknown job, 409 for completed job, 200 for pending job
- **Scan tests**: scan_directory breaks on cancel_event, returns partial results on cancel
- **Frontend tests**: abort button shown during scan, abort calls cancel endpoint, UI shows cancelled state
- **InMemoryJobQueue**: cancel() no-op tests

## Changes Made

| File | Change |
|------|--------|
| `src/stoat_ferret/jobs/queue.py` | Added CANCELLED to JobStatus, cancel_event to _AsyncJobEntry, cancel() to AsyncioJobQueue and Protocol, no-op cancel() to InMemoryJobQueue, cancel_event check in process_jobs() |
| `src/stoat_ferret/api/services/scan.py` | Added cancel_event kwarg to scan_directory(), cancellation checkpoint in file loop, cancel_event passthrough in make_scan_handler() |
| `src/stoat_ferret/api/routers/jobs.py` | Added POST /api/v1/jobs/{job_id}/cancel endpoint with 200/404/409 responses |
| `gui/src/components/ScanModal.tsx` | Added abort button during scan, cancelling/cancelled states, cancel API call, cancelled UI message |
| `docs/design/05-api-specification.md` | Documented cancel endpoint and CANCELLED status |
| `tests/test_jobs/test_asyncio_queue.py` | 5 new cancellation tests |
| `tests/test_api/test_jobs.py` | 3 new cancel endpoint tests |
| `tests/test_api/test_videos.py` | 2 new scan cancellation tests |
| `tests/test_doubles/test_inmemory_job_queue.py` | 2 new cancel no-op tests |
| `gui/src/components/__tests__/ScanModal.test.tsx` | 3 new frontend cancel tests |

## Quality Gates

- ruff check: PASS (0 errors)
- ruff format: PASS (118 files formatted)
- mypy: PASS (49 source files, 0 issues)
- pytest: PASS (960 passed, 20 skipped, 92.9% coverage)
- vitest: PASS (146 tests passed)
