# Implementation Plan — async-scan-endpoint

## Overview

Refactor scan endpoint to submit jobs to the async queue and add a job status polling endpoint.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret/api/routers/videos.py` | Refactor scan endpoint to return job ID |
| Create | `src/stoat_ferret/api/routers/jobs.py` | GET /jobs/{id} status endpoint |
| Modify | `src/stoat_ferret/api/app.py` | Register jobs router |
| Modify | `src/stoat_ferret/api/services/scan.py` | Wrap scan as a job-compatible coroutine |
| Create | `src/stoat_ferret/api/models/job.py` | Job response Pydantic models |
| Modify | `tests/test_api/test_videos.py` | Update scan tests to async pattern |
| Create | `tests/test_api/test_jobs.py` | Job status endpoint tests |

## Implementation Stages

### Stage 1: Job Response Models
Create Pydantic models: `JobSubmitResponse(job_id: str)`, `JobStatusResponse(job_id: str, status: str, progress: float | None, result: Any | None, error: str | None)`.

### Stage 2: Refactor Scan Endpoint
Modify `POST /videos/scan` to create a job ID, submit the scan coroutine to the job queue, and return `JobSubmitResponse`. The scan logic in `scan.py` remains unchanged but is wrapped as a job.

### Stage 3: Add Jobs Router
Create `GET /jobs/{job_id}` endpoint that queries the job queue for status. Return 404 for unknown job IDs.

### Stage 4: Migrate Scan Tests
Update existing scan tests in `test_videos.py` to: POST scan → get job ID → poll GET /jobs/{id} until complete → verify results.

## Quality Gates

- Integration tests: 6–10 tests
- All existing API tests pass (migrated)
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes
- Scan endpoint returns in < 100ms (non-blocking)

## Risks

| Risk | Mitigation |
|------|------------|
| Existing test migration complexity | Incremental — migrate one test at a time |
| Job completion timing in tests | InMemoryJobQueue executes synchronously — deterministic |

## Commit Message

```
feat: make scan endpoint async with job queue pattern
```
