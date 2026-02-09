---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-async-scan-endpoint

## Summary

Refactored `POST /videos/scan` from a blocking endpoint to an async job submission pattern. The endpoint now returns `202 Accepted` with a `job_id` immediately, and callers poll `GET /api/v1/jobs/{job_id}` for status and results.

## Acceptance Criteria

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1 | `POST /videos/scan` returns `{"job_id": "..."}` instead of blocking ScanResponse | PASS |
| FR-2 | `GET /jobs/{id}` returns job status, progress, and result when complete | PASS |
| FR-3 | Job failure returns error status with descriptive message | PASS |
| FR-4 | Scan operation runs as a job in the AsyncJobQueue | PASS |
| FR-5 | Existing scan tests updated to use async pattern (submit + poll) | PASS |

## Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-1 | `POST /videos/scan` returns immediately (< 100ms) | PASS — endpoint validates path and submits to queue without blocking |
| NFR-2 | Job ID is a UUID string | PASS — verified by test |
| NFR-3 | `GET /jobs/{id}` returns 404 for unknown job IDs | PASS |

## Changes Made

### New Files
- `src/stoat_ferret/api/schemas/job.py` — `JobSubmitResponse` and `JobStatusResponse` Pydantic models
- `src/stoat_ferret/api/routers/jobs.py` — `GET /api/v1/jobs/{job_id}` endpoint
- `tests/test_api/test_jobs.py` — Job endpoint tests (5 tests)

### Modified Files
- `src/stoat_ferret/api/routers/videos.py` — Scan endpoint returns 202 with job ID
- `src/stoat_ferret/api/services/scan.py` — Added `make_scan_handler()` factory and `SCAN_JOB_TYPE` constant
- `src/stoat_ferret/api/app.py` — Register jobs router and scan handler on job queue
- `src/stoat_ferret/jobs/queue.py` — Added `register_handler()` to `InMemoryJobQueue` for deterministic test execution with real handlers
- `tests/test_api/conftest.py` — Inject `InMemoryJobQueue` with scan handler into test app
- `tests/test_blackbox/conftest.py` — Same job queue injection for blackbox tests
- `tests/test_api/test_videos.py` — Migrated all scan tests to async pattern (submit + poll)
- `tests/test_blackbox/test_edge_cases.py` — Updated scan empty directory test to async pattern

## Quality Gates

- **ruff check**: All checks passed
- **ruff format**: All files formatted
- **mypy**: Success, no issues found in 39 source files
- **pytest**: 529 passed, 14 skipped (92.60% coverage)
