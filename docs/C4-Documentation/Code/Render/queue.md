# Render Queue

**Source:** `src/stoat_ferret/render/queue.py`
**Component:** Render Engine

## Purpose

Provides a persistent FIFO job queue with configurable concurrency and depth limits. Queue state is persisted via the render repository (database-backed), enabling server restart recovery. Uses asyncio locks to prevent over-committing concurrent jobs.

## Public Interface

### Classes

- `RenderQueue`: Persistent render job queue with concurrency control
  - `__init__(repository: AsyncRenderRepository, max_concurrent: int = 4, max_depth: int = 50) -> None`: Initialize with repository and limits
  - `enqueue(job: RenderJob) -> RenderJob`: Check queue depth, persist via repository, update render_queue_depth metric; raises `QueueFullError` if at capacity
  - `dequeue() -> RenderJob | None`: Acquire asyncio.Lock, check active_count < max_concurrent, fetch FIFO first job by created_at, transition to RUNNING; returns None if no jobs or at capacity
  - `get_active_count() -> int`: Count jobs with RUNNING status via repository
  - `get_queue_depth() -> int`: Count jobs with QUEUED status via repository
  - `recover() -> list[RenderJob]`: Mark all RUNNING jobs as FAILED (server restart recovery), log interrupted jobs with progress preserved

### Exceptions

- `QueueFullError(queue_depth: int, max_depth: int)`: Raised when queue is at capacity; includes current depth and maximum for error messaging

## Dependencies

### Internal Dependencies

- `stoat_ferret.render.render_repository.AsyncRenderRepository`: Protocol for render job persistence
- `stoat_ferret.render.models.RenderJob, RenderStatus`: Job model and status enum
- `stoat_ferret.render.metrics.render_queue_depth`: Prometheus gauge for queue depth

### External Dependencies

- `asyncio`: Lock for dequeue concurrency control
- `structlog`: Structured logging

## Key Implementation Details

### Concurrency Control

`dequeue()` uses an `asyncio.Lock` to serialize access. Inside the lock:
1. Checks `get_active_count() < max_concurrent`
2. Fetches the oldest QUEUED job (FIFO by `created_at`)
3. Transitions job to RUNNING status via repository

This prevents multiple concurrent dequeue calls from exceeding `max_concurrent`.

### Depth Limiting

`enqueue()` checks `get_queue_depth() >= max_depth` before persisting. Raises `QueueFullError` with both current depth and max for informative error responses.

### Server Restart Recovery

`recover()` queries all RUNNING jobs (which were interrupted by server restart) and marks them as FAILED. Progress values are preserved in the failed jobs for inspection. Returns the list of recovered jobs for upstream handling (e.g., checkpoint-based resume).

### Prometheus Metrics

Updates `render_queue_depth` gauge after every enqueue operation to reflect current queue size.

## Relationships

- **Used by:** RenderService (enqueue, dequeue, recover, get_active_count, get_queue_depth), API Gateway (render router for queue status endpoint)
- **Uses:** AsyncRenderRepository (persistence), Prometheus metrics (render_queue_depth)
