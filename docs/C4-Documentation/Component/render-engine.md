# Render Engine

## Purpose

The Render Engine component manages the complete lifecycle of video render jobs: pre-flight validation (settings, disk space, queue capacity), persistent job queuing with concurrency control, FFmpeg subprocess execution with real-time progress tracking via Rust bindings, crash recovery through write-once segment checkpoints, hardware encoder detection and caching, and Prometheus metrics instrumentation. It follows the degraded-but-healthy pattern for health reporting and uses WebSocket event broadcasting with per-job throttling for real-time client updates.

## Responsibilities

- Orchestrate the render job lifecycle: submit, validate, queue, execute, complete/fail/cancel with retry logic
- Manage FFmpeg subprocesses asynchronously with progress parsing delegated to Rust `parse_ffmpeg_progress` and `calculate_progress` bindings
- Enforce render job state machine (QUEUED -> RUNNING -> COMPLETED|FAILED|CANCELLED, FAILED -> QUEUED for retry) at both model and repository levels
- Provide persistent FIFO job queue with configurable concurrency limits (`max_concurrent`, default 4) and depth limits (`max_depth`, default 50)
- Support crash recovery via write-once per-segment checkpoints: on server restart, recover interrupted RUNNING jobs and identify resume points
- Detect and cache hardware encoders (NVENC, QSV, AMF, VideoToolbox) with on-demand refresh
- Broadcast throttled WebSocket events (RENDER_QUEUED, RENDER_STARTED, RENDER_PROGRESS, RENDER_FRAME_AVAILABLE, RENDER_COMPLETED, RENDER_FAILED, RENDER_CANCELLED, RENDER_QUEUE_STATUS)
- Implement graceful shutdown: reject new requests, send stdin 'q' to active FFmpeg processes, wait grace period, force-kill remaining, clean temp files
- Define Prometheus metrics as module-level singletons (LRN-137): render_jobs_total, render_duration_seconds, render_speed_ratio, render_queue_depth, render_encoder_active, render_disk_usage_bytes

## Interfaces

### Provided Interfaces

**RenderService (orchestration)**
- `submit_job(project_id, output_path, output_format, quality_preset, render_plan_json) -> RenderJob` — Pre-flight validation, create, enqueue, broadcast
- `run_job(job, command) -> None` — Execute via executor with progress callback, handle completion/failure/retry
- `cancel_job(job_id) -> bool` — Cancel executor, update status, broadcast
- `recover() -> list[tuple[str, int]]` — Delegate to queue and checkpoint recovery
- `initiate_shutdown() -> None` — Set shutdown flag

**RenderExecutor (process management)**
- `execute(job, command, total_duration_us) -> bool` — Async FFmpeg subprocess with progress parsing
- `cancel(job_id) -> bool` — Graceful stdin 'q' cancellation (Windows-safe)
- `cancel_all() -> list[str]` — Cancel all active processes
- `kill_remaining() -> list[str]` — Force-kill after grace period

**RenderQueue (job scheduling)**
- `enqueue(job) -> RenderJob` — Persist and queue with depth check
- `dequeue() -> RenderJob | None` — FIFO with concurrency limit via asyncio.Lock
- `recover() -> list[RenderJob]` — Mark interrupted RUNNING jobs as FAILED

**AsyncRenderRepository (protocol)**
- `create(job) -> RenderJob`
- `get(job_id) -> RenderJob | None`
- `get_by_project(project_id) -> list[RenderJob]`
- `list_by_status(status) -> list[RenderJob]`
- `update_status(job_id, status, error_message=None) -> None`
- `update_progress(job_id, progress) -> None`
- `list_jobs(status=None, limit=20, offset=0) -> tuple[list[RenderJob], int]`
- `delete(job_id) -> bool`

**CheckpointManager (crash recovery)**
- `write_checkpoint(job_id, segment_index) -> None`
- `get_next_segment(job_id, total_segments) -> int | None`
- `recover() -> list[tuple[str, int]]`
- `cleanup_stale(job_ids) -> int`

**AsyncEncoderCacheRepository (protocol)**
- `get_all() -> list[EncoderCacheEntry]`
- `create_many(entries) -> list[EncoderCacheEntry]`
- `clear() -> None`

**RenderJob (domain model)**
- State machine with validated transitions: `complete()`, `fail(error)`, `retry()`, `cancel()`
- Factory: `create(project_id, output_path, output_format, quality_preset, render_plan) -> RenderJob`

**Prometheus Metrics (module-level singletons)**
- `render_jobs_total` — Counter(labels=["status"])
- `render_duration_seconds` — Histogram with render-specific buckets
- `render_speed_ratio` — Gauge for real-time/wall-clock ratio
- `render_queue_depth` — Gauge for current queue size
- `render_encoder_active` — Gauge(labels=["encoder_name"])
- `render_disk_usage_bytes` — Gauge for output directory usage

**Exceptions**
- `PreflightError(reason)` — Pre-flight validation failure
- `RenderUnavailableError(reason)` — Service unavailable (shutdown, FFmpeg missing)
- `QueueFullError(queue_depth, max_depth)` — Queue at capacity

### Required Interfaces

- **Rust Core:** `validate_render_settings()`, `estimate_output_size()`, `parse_ffmpeg_progress()`, `calculate_progress()` (optional, guarded by `_HAS_RUST_BINDINGS`)
- **WebSocket Manager:** `broadcast(message: dict)` — For event broadcasting
- **Settings:** Application configuration for timeouts, limits, thresholds

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Service | `src/stoat_ferret/render/service.py` | RenderService — job lifecycle orchestration, pre-flight validation, progress throttling, retry logic |
| Executor | `src/stoat_ferret/render/executor.py` | RenderExecutor — FFmpeg subprocess management, progress parsing via Rust, graceful cancellation |
| Queue | `src/stoat_ferret/render/queue.py` | RenderQueue — persistent FIFO queue with concurrency/depth limits, server restart recovery |
| Models | `src/stoat_ferret/render/models.py` | RenderJob, RenderStatus, OutputFormat, QualityPreset, validate_render_transition |
| Repository | `src/stoat_ferret/render/render_repository.py` | AsyncRenderRepository protocol, AsyncSQLiteRenderRepository, InMemoryRenderRepository |
| Checkpoints | `src/stoat_ferret/render/checkpoints.py` | CheckpointManager — write-once segment checkpoints for crash recovery |
| Encoder Cache | `src/stoat_ferret/render/encoder_cache.py` | EncoderCacheEntry, AsyncEncoderCacheRepository protocol and implementations |
| Metrics | `src/stoat_ferret/render/metrics.py` | Prometheus metric singletons for render subsystem (LRN-137) |

## Key Behaviors

**State Machine Enforcement:** The render job state machine (QUEUED -> RUNNING -> COMPLETED|FAILED|CANCELLED, FAILED -> QUEUED) is enforced at two levels: model methods (`complete()`, `fail()`, `retry()`, `cancel()`) and repository updates (`validate_render_transition()`). This defense-in-depth prevents invalid transitions regardless of caller.

**Persistent Queue via Repository:** Queue state is stored in the database (render_jobs status column), not in-memory. This enables recovery after server restarts — `RenderQueue.recover()` marks interrupted RUNNING jobs as FAILED, and `CheckpointManager.recover()` identifies resume points.

**Progress Throttling:** Two independent mechanisms reduce WebSocket traffic per job: progress events use 0.5s minimum interval AND 5% delta threshold; frame events use max 2/second rate limit. State is tracked per-job-per-event-type in dictionaries.

**Graceful Process Termination (Windows-Safe):** Instead of `process.terminate()`, sends `q\n` via stdin — FFmpeg's native quit command. This ensures clean file finalization on all platforms. Falls back to `process.kill()` after configurable grace period (default 10s).

**Hardware Encoder Detection Caching:** FFmpeg encoder detection results are cached in SQLite (`encoder_cache` table). The API provides lazy detection (cache on first request) and forced refresh (clear + re-detect). An asyncio lock prevents concurrent detection subprocess calls.

**Rust Binding Fallback:** All Rust binding imports (`validate_render_settings`, `estimate_output_size`, `parse_ffmpeg_progress`, `calculate_progress`) use try/except guards. When `_HAS_RUST_BINDINGS` is False, pre-flight skips Rust validation and falls back to conservative estimates.

**Metric Singleton Module Pattern (LRN-137):** All Prometheus metrics defined as module-level constants in `metrics.py`. Service files import specific metric objects, providing a single inventory and avoiding duplicate registration.

## Inter-Component Relationships

```
API Gateway (Render Router)
    |-- uses --> Render Engine (RenderService, RenderQueue, AsyncRenderRepository)
    |-- uses --> Render Engine (AsyncEncoderCacheRepository)

API Gateway (Health Router)
    |-- checks --> Render Engine (queue depth, active jobs, disk usage, encoder availability)

API Gateway (WebSocket Manager)
    <-- broadcasts to -- Render Engine (RenderService throttled events)

API Gateway (App Factory / Lifespan)
    |-- creates --> Render Engine (RenderService, RenderQueue, RenderExecutor, CheckpointManager)
    |-- calls --> Render Engine (recover on startup, graceful shutdown sequence)

Rust Core
    <-- delegates to -- Render Engine (validate_render_settings, estimate_output_size, parse_ffmpeg_progress, calculate_progress)

Data Access (Schema)
    |-- defines tables for --> Render Engine (render_jobs, render_checkpoints, encoder_cache)

Observability
    |-- reads metrics from --> Render Engine (Prometheus metrics at /metrics)
```

## Version History

| Version | Changes |
|---------|---------|
| v029 | Initial Render Engine component documentation: service, executor, queue, models, repository, checkpoints, encoder cache, metrics |
