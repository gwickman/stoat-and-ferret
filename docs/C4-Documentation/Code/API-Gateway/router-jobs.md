# Jobs Router

**Source:** `src/stoat_ferret/api/routers/jobs.py`
**Component:** API Gateway

## Purpose

Job status polling and cancellation endpoints. Allows clients to track the status of async background jobs (scans, renders) and request job cancellation if still queued/running.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/jobs/{job_id} | Get job status |
| POST | /api/v1/jobs/{job_id}/cancel | Request job cancellation |

### Functions

- `get_job_status(job_id: str, request: Request) -> JobStatusResponse`: Returns job status including progress, result when complete, and error on failure. 404 if job_id not found.

- `cancel_job(job_id: str, request: Request) -> JobStatusResponse`: Requests job cancellation. Only succeeds if job is queued/running. Returns updated status after cancellation. 404 if job not found, 409 if already in terminal state (COMPLETE, FAILED, TIMEOUT, CANCELLED).

## Key Implementation Details

- **Status values**: Mapped from JobStatus enum (from jobs.queue module); includes QUEUED, RUNNING, COMPLETE, FAILED, TIMEOUT, CANCELLED
- **Progress field**: Optional float 0.0-1.0 for in-progress jobs; None for queued or terminal jobs
- **Result field**: Contains job-specific result data when status is COMPLETE; None otherwise
- **Error field**: Contains error message string when status is FAILED; None for successful jobs
- **Terminal states**: COMPLETE, FAILED, TIMEOUT, CANCELLED; cannot cancel job already in terminal state
- **Cancel semantics**: Sets cancel flag on job; job queue processes the flag and transitions job to CANCELLED state
- **Re-fetch after cancel**: cancel_job refetches result after setting cancel flag to return updated status

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.job.JobStatusResponse`: Job status response schema
- `stoat_ferret.jobs.queue.JobStatus`: Job status enum

### External Dependencies

- `fastapi`: APIRouter, HTTPException, Request, status

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Job queue (via app.state.job_queue) for status retrieval and cancellation
