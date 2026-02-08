# Implementation Plan — job-queue-infrastructure

## Overview

Create the AsyncJobQueue protocol and asyncio.Queue-based implementation with FastAPI lifespan integration.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret/jobs/queue.py` | Add AsyncioJobQueue implementation alongside protocol |
| Create | `src/stoat_ferret/jobs/worker.py` | Job worker coroutine for processing queue |
| Create | `src/stoat_ferret/jobs/models.py` | Job status enum, JobResult dataclass |
| Modify | `src/stoat_ferret/api/app.py` | Integrate job queue and worker into lifespan |
| Create | `tests/test_jobs/test_asyncio_queue.py` | AsyncioJobQueue unit tests |
| Create | `tests/test_jobs/test_worker.py` | Worker lifecycle tests |
| Create | `tests/test_jobs/__init__.py` | Package init |

## Implementation Stages

### Stage 1: Job Models
Create `JobStatus` enum (pending, running, completed, failed) and `JobResult` dataclass with status, result, error fields.

### Stage 2: AsyncioJobQueue
Implement `AsyncioJobQueue` using `asyncio.Queue`. Track job status in an internal dict. Support configurable timeout (default 5 minutes).

### Stage 3: Worker Coroutine
Create `process_jobs()` coroutine that pulls from the queue and executes jobs. Handle timeout and cancellation gracefully.

### Stage 4: Lifespan Integration
Modify `lifespan()` in `app.py` to create job queue, start worker task, and cancel on shutdown. Store queue on `app.state.job_queue`.

## Quality Gates

- AsyncioJobQueue tests: 5–8 tests
- Worker tests: 2–3 tests
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes
- Existing tests pass (lifespan changes don't break anything)

## Risks

| Risk | Mitigation |
|------|------------|
| Worker task leak on shutdown | Explicit cancellation in lifespan cleanup |
| Timeout values need tuning | Configurable defaults; tune at runtime (U1) |

## Commit Message

```
feat: add async job queue infrastructure with asyncio.Queue
```
