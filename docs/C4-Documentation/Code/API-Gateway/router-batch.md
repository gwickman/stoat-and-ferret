# Batch Render Router

**Source:** `src/stoat_ferret/api/routers/batch.py`
**Component:** API Gateway

## Purpose

Batch render job submission and progress tracking endpoints. Manages submission of multiple parallel render jobs with concurrency limits and aggregated progress reporting.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/render/batch | Submit batch of render jobs |
| GET | /api/v1/render/batch/{batch_id} | Get batch progress |

### Functions

- `submit_batch(batch_request: BatchRequest, request: Request) -> BatchResponse`: Submits batch of render jobs. Validates job count <= Settings.batch_max_jobs. Creates batch with unique batch_id, assigns unique job_ids, queues jobs with asyncio.Semaphore for concurrency control. Returns 202 Accepted with batch_id. 422 if job count exceeds limit.

- `get_batch_progress(batch_id: str, request: Request) -> BatchProgressResponse`: Returns aggregated batch progress using Rust calculate_batch_progress(). Includes per-job status details (job_id, project_id, status, progress, error). 404 if batch_id not found.

### Helper Functions

- `_get_batch_store(request: Request) -> dict[str, _BatchState]`: Gets or lazily creates batch store on app.state._batch_store
- `_to_rust_status(job: _BatchJob) -> BatchJobStatus`: Converts internal job status string to Rust BatchJobStatus enum
- `_run_batch_job(job: _BatchJob, semaphore: asyncio.Semaphore, handler: BatchRenderHandler | None) -> None`: Executes single batch job with semaphore-limited concurrency. Calls handler if provided.

### Internal Classes

- `_BatchJob`: Tracks single job in batch with fields: job_id, project_id, output_path, quality, status, progress, error
- `_BatchState`: Tracks batch with fields: batch_id, jobs list

## Key Implementation Details

- **Concurrency management**: Uses asyncio.Semaphore(Settings.batch_parallel_limit) to limit parallel job execution; allows sequential queue with built-in concurrency control
- **Async execution**: Jobs run as asyncio.create_task() without blocking batch submission; returns 202 immediately
- **Batch state storage**: In-memory dict mapping batch_id -> _BatchState; persists for session lifetime
- **Job statuses**: "queued" (initial), "running", "complete", "failed" (on exception)
- **Progress tracking**: Job.progress updated to 1.0 on completion; can be updated by handler
- **Render handler**: Optional async callable (project_id, output_path, quality) -> None; if provided, called during job execution
- **Rust progress aggregation**: calculate_batch_progress() takes list of BatchJobStatus (from Rust); returns aggregate with overall_progress, completed_jobs, failed_jobs, total_jobs
- **Logging**: Structured logs for batch submission, job start/completion/failure

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.batch.*`: BatchJobStatusResponse, BatchProgressResponse, BatchRequest, BatchResponse
- `stoat_ferret.api.settings.get_settings`: Settings for batch_parallel_limit, batch_max_jobs
- `stoat_ferret_core.*`: BatchJobStatus, calculate_batch_progress (Rust bindings)

### External Dependencies

- `fastapi`: APIRouter, HTTPException, Request, status
- `asyncio.Semaphore, asyncio.create_task`: Async concurrency control
- `uuid.uuid4`: ID generation
- `dataclasses.dataclass, field`: Internal data structures
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Settings for limits, Rust core for progress calculation, optional batch render handler from app.state
