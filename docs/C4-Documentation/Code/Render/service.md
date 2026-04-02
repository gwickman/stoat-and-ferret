# Render Service

**Source:** `src/stoat_ferret/render/service.py`
**Component:** Render Engine

## Purpose

Orchestrates the full render job lifecycle: pre-flight validation (settings, disk space, queue capacity), job submission and queueing, execution with progress tracking, completion/failure handling with retry logic, and WebSocket event broadcasting with throttling.

## Public Interface

### Classes

- `RenderService`: Main render orchestration service
  - `__init__(queue: RenderQueue, executor: RenderExecutor, checkpoint_manager: CheckpointManager, broadcast: Callable, settings: Settings) -> None`: Initialize with dependencies
  - `submit_job(project_id: str, output_path: str, output_format: str, quality_preset: str, render_plan_json: str) -> RenderJob`: Validate settings, check disk space and queue capacity, create and enqueue job, broadcast RENDER_QUEUED and RENDER_STARTED events
  - `run_job(job: RenderJob, command: list[str]) -> None`: Execute render via executor with progress callback, log milestones at 25/50/75/100%, handle completion or failure with retry
  - `cancel_job(job_id: str) -> bool`: Cancel executor process, update status to CANCELLED, broadcast RENDER_CANCELLED, clear throttle state
  - `recover() -> list[tuple[str, int]]`: Delegate to queue and checkpoint recovery, return (job_id, next_segment_index) pairs
  - `initiate_shutdown() -> None`: Set shutdown flag to reject new requests

### Exceptions

- `PreflightError(reason: str)`: Pre-flight validation failures (invalid settings, insufficient disk, queue full)
- `RenderUnavailableError(reason: str)`: Service unavailable (shutdown in progress, FFmpeg not found)

## Dependencies

### Internal Dependencies

- `stoat_ferret.render.queue.RenderQueue`: Job queuing with concurrency limits
- `stoat_ferret.render.executor.RenderExecutor`: FFmpeg process management
- `stoat_ferret.render.checkpoints.CheckpointManager`: Crash recovery via segment checkpoints
- `stoat_ferret.render.models.RenderJob`: Job data model with state machine
- `stoat_ferret.render.metrics`: Prometheus metrics (render_jobs_total, render_duration_seconds)
- `stoat_ferret.api.settings.Settings`: Application configuration
- `stoat_ferret.api.websocket.events`: WebSocket event building (RENDER_QUEUED, RENDER_STARTED, RENDER_PROGRESS, RENDER_FRAME_AVAILABLE, RENDER_COMPLETED, RENDER_FAILED, RENDER_CANCELLED)

### External Dependencies

- `stoat_ferret_core._core.validate_render_settings`: Rust binding for settings validation (optional, guarded by `_HAS_RUST_BINDINGS`)
- `stoat_ferret_core._core.estimate_output_size`: Rust binding for output size estimation (optional)
- `structlog`: Structured logging
- `shutil`: Disk space checking via `shutil.disk_usage()`

## Key Implementation Details

### Pre-Flight Validation

`submit_job()` performs three checks before accepting a job:
1. **Settings validation** — Delegates to Rust `validate_render_settings()` if bindings available; validates format, codec, and fps
2. **Disk space** — Calls `estimate_output_size()` and compares against available space via `shutil.disk_usage()`
3. **Queue capacity** — Checks current queue depth against `max_depth` setting

### Progress Throttling

Two independent throttle mechanisms reduce WebSocket traffic:
- **Progress events**: Minimum 0.5s interval AND 5% delta threshold between broadcasts
- **Frame events**: Maximum 2 per second rate limit

State tracked per-job-per-event-type in dictionaries:
- `_last_progress_time: dict[str, float]` — Last broadcast timestamp per job
- `_last_progress_value: dict[str, float]` — Last broadcast progress value per job

### Milestone Logging

Progress milestones logged at 25%, 50%, 75%, and 100% via structlog with job_id context.

### Retry Logic

On failure, `_handle_failure()` checks `retry_count < max_retries` (from settings). If retryable, calls `job.retry()` (resets progress, increments retry_count) and re-enqueues. Otherwise broadcasts RENDER_FAILED.

### Rust Binding Fallback

Both `validate_render_settings` and `estimate_output_size` are imported with a try/except guard. When `_HAS_RUST_BINDINGS` is False, pre-flight skips Rust validation and uses a conservative size estimate.

## Relationships

- **Used by:** API Gateway (render router via dependency injection on `app.state`)
- **Uses:** RenderQueue, RenderExecutor, CheckpointManager, WebSocket broadcast function, Prometheus metrics
- **Broadcasts to:** WebSocket ConnectionManager (RENDER_QUEUED, RENDER_STARTED, RENDER_PROGRESS, RENDER_FRAME_AVAILABLE, RENDER_COMPLETED, RENDER_FAILED, RENDER_CANCELLED)
