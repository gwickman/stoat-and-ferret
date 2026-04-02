# Render Router

**Source:** `src/stoat_ferret/api/routers/render.py`
**Component:** API Gateway

## Purpose

REST API endpoints for the render job lifecycle: submit, query, cancel, retry, delete jobs; list and refresh hardware encoders; query supported formats; and monitor queue status. Uses asyncio locks for state transition serialization and encoder refresh concurrency control.

## Public Interface

### Dependency Injection Functions

- `get_encoder_cache_repository(request: Request) -> AsyncEncoderCacheRepository`: Retrieve encoder cache from app.state
- `get_render_repository(request: Request) -> AsyncRenderRepository`: Retrieve render repository from app.state
- `get_render_service(request: Request) -> RenderService`: Retrieve render service; raises 503 if unavailable
- `get_render_queue(request: Request) -> RenderQueue`: Retrieve render queue; raises 503 if unavailable

### Type Aliases

- `RenderRepoDep = Annotated[AsyncRenderRepository, Depends(get_render_repository)]`
- `RenderServiceDep = Annotated[RenderService, Depends(get_render_service)]`
- `RenderQueueDep = Annotated[RenderQueue, Depends(get_render_queue)]`
- `EncoderCacheDep = Annotated[AsyncEncoderCacheRepository, Depends(get_encoder_cache_repository)]`

### Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | /api/v1/render | 201 | Submit a new render job |
| GET | /api/v1/render/{job_id} | 200 | Get render job by ID |
| GET | /api/v1/render | 200 | List render jobs (paginated, filterable by status) |
| POST | /api/v1/render/{job_id}/cancel | 200 | Cancel a running/queued job |
| POST | /api/v1/render/{job_id}/retry | 200 | Retry a failed job |
| DELETE | /api/v1/render/{job_id} | 200 | Delete job metadata (output files preserved) |
| GET | /api/v1/render/encoders | 200 | List detected encoders (lazy-detects if cache empty) |
| POST | /api/v1/render/encoders/refresh | 200 | Force re-detection of hardware encoders |
| GET | /api/v1/render/formats | 200 | List supported output formats with codecs and presets |
| GET | /api/v1/render/queue | 200 | Queue status: active/pending counts, disk space, throughput |

### Request/Response Models

- `CreateRenderRequest`: project_id, output_format, quality_preset, render_plan
- `RenderJobResponse`: Full job state including id, status, progress, error_message, retry_count, timestamps
- `RenderListResponse`: Paginated list (items, total, limit, offset)
- `EncoderListResponse`: encoders list with cached flag
- `FormatListResponse`: Supported formats with codecs and quality presets
- `QueueStatusResponse`: active_jobs, pending_jobs, disk_space, daily_throughput

### Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Invalid format or preset value |
| 404 | Job not found |
| 409 | Job not cancellable (wrong status), retry limit exceeded, encoder refresh in progress |
| 422 | Pre-flight failure (disk space, queue capacity, settings validation) |
| 503 | Render service unavailable (shutdown, FFmpeg missing) |

## Dependencies

### Internal Dependencies

- `stoat_ferret.render.service.RenderService, PreflightError, RenderUnavailableError`: Render orchestration
- `stoat_ferret.render.queue.RenderQueue, QueueFullError`: Job queuing
- `stoat_ferret.render.render_repository.AsyncRenderRepository`: Job persistence
- `stoat_ferret.render.encoder_cache.AsyncEncoderCacheRepository`: Encoder cache
- `stoat_ferret.render.models.RenderStatus`: Status enum for filtering
- `stoat_ferret.api.schemas.render`: Request/response Pydantic models

### External Dependencies

- `fastapi`: Router, Depends, Request, HTTPException, status
- `asyncio`: Lock for state transitions and encoder refresh

## Key Implementation Details

### Concurrency Locks

- `_state_transition_lock: asyncio.Lock` — Serializes cancel and retry operations to prevent race conditions (NFR-003)
- `_encoder_refresh_lock: asyncio.Lock` — Prevents concurrent encoder detection subprocess calls (NFR-002)

### Submit Job Flow

POST /api/v1/render:
1. Validates output_format and quality_preset against allowed values
2. Calls `render_service.submit_job()` which runs pre-flight checks
3. Returns 201 with RenderJobResponse
4. On PreflightError: returns 422 with reason
5. On RenderUnavailableError: returns 503

### Encoder Lazy Detection

GET /api/v1/render/encoders:
1. Checks encoder cache via `get_all()`
2. If cache empty, acquires `_encoder_refresh_lock`
3. If lock unavailable (refresh in progress), returns empty list with cached=False
4. If lock acquired, runs FFmpeg encoder detection subprocess, stores results
5. Returns detected encoders

### Static Formats Endpoint

GET /api/v1/render/formats returns hardcoded supported format data (no database or service dependencies), making it always available even during service unavailability.

## Relationships

- **Used by:** API Gateway (included as router), Web GUI (render controls), AI Agent (programmatic rendering)
- **Uses:** RenderService, RenderQueue, AsyncRenderRepository, AsyncEncoderCacheRepository
