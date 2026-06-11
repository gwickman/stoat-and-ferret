# C4 Code Level: API Routers

## Overview

- **Name**: HTTP Route Handlers for Core Domain Operations
- **Description**: FastAPI routers providing REST endpoints for health checks, render jobs, preview sessions, and job queue operations.
- **Location**: `src/stoat_ferret/api/routers/`
- **Language**: Python
- **Purpose**: Exposes domain business logic via HTTP endpoints with dependency injection and error handling.
- **Parent Component**: [API Gateway](./c4-component-api-gateway.md)

## Code Elements

### Health Router (health.py)

#### Functions
- `async liveness() -> dict[str, str]` - Simple liveness probe
- `async readiness(request: Request) -> JSONResponse` - Full dependency health checks
- `async _check_database(request: Request) -> dict[str, Any]` - Database connectivity check
- `async _check_ffmpeg() -> dict[str, Any]` - FFmpeg availability check
- `async _check_preview(request: Request) -> dict[str, Any]` - Preview cache status
- `async _check_proxy(request: Request) -> dict[str, Any]` - Proxy directory health
- `async _check_render(request: Request) -> dict[str, Any]` - Render queue health

### Jobs Router (jobs.py)

#### Functions
- `async get_job_status(job_id: str, request: Request) -> JobStatusResponse` - Get job status
- `async cancel_job(job_id: str, request: Request) -> JobStatusResponse` - Cancel job

### Render Router (render.py)

#### Dependency Injection Functions
- `async get_encoder_cache_repository(request: Request) -> AsyncEncoderCacheRepository`
- `async get_render_repository(request: Request) -> AsyncRenderRepository`
- `async get_render_service(request: Request) -> RenderService`
- `async get_render_queue(request: Request) -> RenderQueue`

#### Endpoints
- `async create_render_job(body: CreateRenderRequest, render_service: RenderServiceDep) -> RenderJobResponse`
- `async get_encoders(encoder_repo: EncoderCacheDep) -> EncoderListResponse`
- `async refresh_encoders(encoder_repo: EncoderCacheDep) -> EncoderListResponse`
- `async get_output_formats() -> FormatListResponse`
- `def render_preview(body: RenderPreviewRequest) -> RenderPreviewResponse`
- `async get_queue_status(queue: RenderQueueDep, repo: RenderRepoDep) -> QueueStatusResponse`
- `async get_render_job(job_id: str, repo: RenderRepoDep) -> RenderJobResponse`
- `async list_render_jobs(repo: RenderRepoDep, limit: int, offset: int, status_filter: str) -> RenderListResponse`
- `async cancel_render_job(job_id: str, repo: RenderRepoDep, render_service: RenderServiceDep) -> RenderJobResponse`
- `async retry_render_job(job_id: str, repo: RenderRepoDep) -> RenderJobResponse`
- `async delete_render_job(job_id: str, repo: RenderRepoDep) -> RenderJobResponse`

### Preview Router (preview.py)

#### Endpoints
- `async get_cache_status(request: Request) -> PreviewCacheStatusResponse`
- `async clear_cache(request: Request) -> PreviewCacheClearResponse`
- `async start_preview(project_id: str, request: Request, body: PreviewStartRequest) -> PreviewStartResponse`
- `async get_preview_status(session_id: str, request: Request) -> PreviewStatusResponse`
- `async seek_preview(session_id: str, body: PreviewSeekRequest, request: Request) -> PreviewSeekResponse`
- `async stop_preview(session_id: str, request: Request) -> PreviewStopResponse`
- `async get_manifest(session_id: str, request: Request) -> Response`
- `async get_segment(session_id: str, index: int, request: Request) -> Response`

### Projects Router (projects.py)

Provides CRUD operations for projects and clips under `/api/v1/projects`.

#### Dependency Injection Functions
- `async get_project_repository(request: Request) -> AsyncProjectRepository` - Returns injected or SQLite project repo from app state
- `async get_clip_repository(request: Request) -> AsyncClipRepository` - Returns injected or SQLite clip repo from app state
- `async get_video_repository(request: Request) -> AsyncVideoRepository` - Returns injected or SQLite video repo from app state

#### Project Endpoints
- `async list_projects(repo: ProjectRepoDep, limit: int, offset: int) -> ProjectListResponse` - `GET /api/v1/projects` — paginated project list
- `async create_project(project_data: ProjectCreate, request: Request, repo: ProjectRepoDep) -> ProjectResponse` - `POST /api/v1/projects` — creates project, broadcasts PROJECT_CREATED WebSocket event
- `async get_project(project_id: str, repo: ProjectRepoDep) -> ProjectResponse` - `GET /api/v1/projects/{project_id}` — 404 if not found
- `async update_project(project_id: str, project_data: ProjectUpdate, repo: ProjectRepoDep) -> ProjectResponse` - `PATCH /api/v1/projects/{project_id}` — partial update
- `async delete_project(project_id: str, repo: ProjectRepoDep) -> Response` - `DELETE /api/v1/projects/{project_id}` — 204 on success

#### Clip Endpoints
- `async list_clips(project_id: str, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> ClipListResponse` - `GET /api/v1/projects/{project_id}/clips` — 404 if project not found
- `async get_clip(project_id: str, clip_id: str, clip_repo: ClipRepoDep) -> ClipResponse` - `GET /api/v1/projects/{project_id}/clips/{clip_id}` — 404 if clip not found or belongs to different project
- `async add_clip(project_id: str, request: ClipCreate, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep, video_repo: VideoRepoDep) -> ClipResponse` - `POST /api/v1/projects/{project_id}/clips` — validates clip via Rust, 400 on validation error
- `async update_clip(project_id: str, clip_id: str, request: ClipUpdate, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep, video_repo: VideoRepoDep) -> ClipResponse` - `PATCH /api/v1/projects/{project_id}/clips/{clip_id}` — re-validates clip via Rust after update
- `async delete_clip(project_id: str, clip_id: str, request: Request, clip_repo: ClipRepoDep) -> Response` - `DELETE /api/v1/projects/{project_id}/clips/{clip_id}` — 204 on success, broadcasts CLIP_DELETED WebSocket event

### Effects Router (effects.py)

Provides effect discovery, preview, application, update, deletion, and transition endpoints under `/api/v1`.

#### Dependency Injection Functions
- `async get_effect_registry(request: Request) -> EffectRegistry` - Returns injected registry or falls back to module-level default registry
- `async _get_project_repository(request: Request) -> AsyncProjectRepository` - Returns injected or SQLite project repo from app state
- `async _get_clip_repository(request: Request) -> AsyncClipRepository` - Returns injected or SQLite clip repo from app state
- `async _get_thumbnail_service(request: Request) -> ThumbnailService` - Returns injected or freshly-created ThumbnailService

#### Effects Discovery and Preview Endpoints
- `async list_effects(registry: RegistryDep) -> EffectListResponse` - `GET /api/v1/effects` — lists all 17 built-in effects with parameter schemas, AI hints, filter preview strings, and automatable parameters
- `async preview_effect(request: EffectPreviewRequest, registry: RegistryDep) -> EffectPreviewResponse` - `POST /api/v1/effects/preview` — validates parameters and returns generated FFmpeg filter string without applying
- `async preview_effect_thumbnail(request: EffectThumbnailRequest, registry: RegistryDep, thumbnail_service: ThumbnailDep) -> FileResponse` - `POST /api/v1/effects/preview/thumbnail` — extracts first frame from video, applies effect, returns 320px-wide JPEG

#### Clip Effect CRUD Endpoints
- `async get_clip_effects(project_id: str, clip_id: str, clip_repo: ClipRepoDep) -> ClipEffectsResponse` - `GET /api/v1/projects/{project_id}/clips/{clip_id}/effects` — returns applied effects list (empty list when none)
- `async apply_effect_to_clip(project_id: str, clip_id: str, request: EffectApplyRequest, registry: RegistryDep, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> EffectApplyResponse` - `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` — validates effect type and parameters, generates filter string, stores effect on clip; increments `stoat_ferret_effect_applications_total` counter
- `async update_clip_effect(project_id: str, clip_id: str, index: int, request: EffectUpdateRequest, registry: RegistryDep, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> EffectApplyResponse` - `PATCH /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index}` — validates index bounds, re-validates parameters, regenerates filter string
- `async delete_clip_effect(project_id: str, clip_id: str, index: int, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> EffectDeleteResponse` - `DELETE /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index}` — removes effect at zero-based index from clip's effects list

#### Transition Endpoint
- `async apply_transition(project_id: str, request: TransitionRequest, registry: RegistryDep, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> EffectTransitionResponse` - `POST /api/v1/projects/{project_id}/effects/transition` — validates source and target clips are adjacent in timeline, generates filter string, stores transition on project; increments `stoat_ferret_transition_applications_total` counter

### System Router (system.py)

Exposes `GET /api/v1/system/state` — a best-effort aggregate snapshot of in-memory job queue, render repository, and WebSocket connection manager state (BL-275).

#### Functions

- `async get_system_state(request: Request) -> SystemState`
  - Description: Return aggregate in-memory system state. Performs a single-pass scan over the job queue (`job_queue.list_jobs()`), `render_repository` (async SQLite reads for RUNNING/QUEUED render jobs, INV-SNAP-1), and WebSocket connection manager. Missing or transiently-broken subsystems are reported as empty collections (NFR-003); snapshot is best-effort. Wraps `_build_system_state()` in a Prometheus histogram timer.
  - Location: system.py:47
  - Route: `GET /api/v1/system/state`
  - Response: `SystemState` schema (active_jobs, active_connections, uptime_seconds, timestamp)

- `async _build_system_state(request: Request) -> SystemState`
  - Description: Inner implementation of `get_system_state()`. Reads `app.state.job_queue.list_jobs()`, `app.state.render_repository.list_by_status(RenderStatus.RUNNING)` and `list_by_status(RenderStatus.QUEUED)`, and `app.state.ws_manager.active_connections`. Each subsystem is accessed via `getattr` with `None` default; exceptions are caught and logged as warnings rather than raised (NFR-003 graceful partial state).
  - Location: system.py:69

- `_compute_uptime_seconds(app_state: object) -> float`
  - Description: Return seconds elapsed since `app.state._startup_timestamp` (ISO8601 string set by lifespan after all subsystems are ready). Returns `0.0` before the startup gate opens.
  - Location: system.py:26

#### render_repository Integration

`get_system_state()` reads `app.state.render_repository` (an `AsyncRenderRepository`) to include active render jobs in the system state snapshot. Only RUNNING and QUEUED render jobs are fetched (not historical completed/failed jobs). Each render job is surfaced as a `JobSummary` with `job_type="render"`. The render repository is accessed via `getattr(app_state, "render_repository", None)` so the endpoint degrades gracefully when the render subsystem is unavailable (NFR-003).

## Dependencies

### Internal Dependencies
- stoat_ferret.api.schemas (job, render, preview, system_state, clip, project, effect)
- stoat_ferret.api.settings
- stoat_ferret.db modules (models, repositories)
- stoat_ferret.jobs.queue (AsyncJobQueue, JobSnapshot)
- stoat_ferret.render (encoder_cache, models, queue, service, repository)
- stoat_ferret.preview (manager, cache)
- stoat_ferret.effects (registry, definitions)
- stoat_ferret.api.services.thumbnail (ThumbnailService)
- stoat_ferret_core (Rust FFI)

### External Dependencies
- fastapi: APIRouter, HTTPException, Request, Response, Query, Depends, status
- structlog: logging
- datetime, pathlib, shutil, subprocess, asyncio

## Relationships

```mermaid
---
title: Routers Module Structure
---
flowchart TB
    subgraph HE["Health Endpoints"]
        LV["liveness"]
        RD["readiness"]
    end

    subgraph JE["Jobs Endpoints"]
        GJ["get_job_status"]
        CJ["cancel_job"]
    end

    subgraph RE["Render Endpoints"]
        CRJ["create_render_job"]
        CRUD["get/list/cancel/retry/delete"]
        ENC["get/refresh encoders"]
        FMT["get formats"]
        PRV["render preview"]
        QS["queue status"]
    end

    subgraph PE["Preview Endpoints"]
        CST["cache status"]
        SESS["session mgmt"]
        HLS["HLS serving"]
    end

    subgraph SE["System Endpoints"]
        SST["get_system_state"]
    end

    subgraph PRJ["Projects Endpoints"]
        PCRUD["project CRUD"]
        CCRUD["clip CRUD"]
    end

    subgraph EFX["Effects Endpoints"]
        LST["list_effects"]
        PREV["preview_effect"]
        THUMB["preview_thumbnail"]
        GFXC["get/apply/update/delete clip effects"]
        TRN["apply_transition"]
    end

    CRUD -.->|dependency| RenderService["RenderService"]
    ENC -.->|dependency| EncoderCache["EncoderCache"]
    SESS -.->|dependency| PreviewMgr["PreviewManager"]
    HLS -.->|reads from| FileSystem["File System"]
    SST -.->|reads| JobQueue["JobQueue.list_jobs()"]
    SST -.->|reads| RenderRepo["RenderRepository"]
    SST -.->|reads| WSManager["WSManager.active_connections"]
    PCRUD -.->|dependency| ProjectRepo["ProjectRepository"]
    CCRUD -.->|dependency| ClipRepo["ClipRepository"]
    GFXC -.->|dependency| EffectReg["EffectRegistry"]
    TRN -.->|dependency| EffectReg
```

## Notes

- Uses asyncio.Lock for encoder refresh and state transition concurrency control
- FFmpeg detection runs in thread pool to avoid event loop blocking
- Health checks return 503 for critical failures, 200 for degraded states
- Follows JSON:API error response patterns
- `get_system_state()` (system.py) integrates `render_repository` to include RUNNING/QUEUED render jobs in the system snapshot alongside generic job-queue jobs; both are surfaced as `JobSummary` entries with distinct `job_type` values (`"render"` vs the registered job type string)
- System state endpoint uses best-effort reads (NFR-003): each subsystem (job_queue, render_repository, ws_manager) is accessed via `getattr` with a `None` fallback; exceptions are caught and logged as warnings, never propagated as HTTP 500
