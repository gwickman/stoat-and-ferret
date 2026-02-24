# C4 Code Level: API Routers

## Overview
- **Name**: API Routers
- **Description**: FastAPI route handlers for health, videos, projects, clips, jobs, effects, transitions, filesystem, and WebSocket endpoints
- **Location**: `src/stoat_ferret/api/routers/`
- **Language**: Python (async/await)
- **Purpose**: Define all REST API and WebSocket endpoints, map HTTP requests to business logic via dependency injection
- **Parent Component**: TBD

## Code Elements

### Functions/Methods

#### health.py

- `async liveness() -> dict[str, str]`
  - Description: Liveness probe -- returns 200 if the server is running (GET /health/live)
  - Location: `src/stoat_ferret/api/routers/health.py:18`
  - Dependencies: None

- `async readiness(request: Request) -> JSONResponse`
  - Description: Readiness probe -- checks database and FFmpeg availability (GET /health/ready)
  - Location: `src/stoat_ferret/api/routers/health.py:31`
  - Dependencies: `_check_database`, `_check_ffmpeg`

- `async _check_database(request: Request) -> dict[str, Any]`
  - Description: Check database connectivity with latency measurement
  - Location: `src/stoat_ferret/api/routers/health.py:64`
  - Dependencies: `app.state.db`

- `async _check_ffmpeg() -> dict[str, Any]`
  - Description: Check FFmpeg availability by running ffmpeg -version via asyncio.to_thread
  - Location: `src/stoat_ferret/api/routers/health.py:86`
  - Dependencies: `subprocess`, `shutil`, `asyncio`

#### videos.py

- `async get_repository(request: Request) -> AsyncVideoRepository`
  - Description: FastAPI dependency -- get video repository from app state or create SQLite fallback
  - Location: `src/stoat_ferret/api/routers/videos.py:34`

- `async list_videos(repo: RepoDep, limit: int, offset: int) -> VideoListResponse`
  - Description: List videos with pagination (GET /api/v1/videos)
  - Location: `src/stoat_ferret/api/routers/videos.py:57`

- `async search_videos(repo: RepoDep, q: str, limit: int) -> VideoSearchResponse`
  - Description: Search videos by filename or path (GET /api/v1/videos/search)
  - Location: `src/stoat_ferret/api/routers/videos.py:84`

- `async get_thumbnail(video_id: str, repo: RepoDep) -> FileResponse`
  - Description: Get thumbnail image for a video, with placeholder fallback (GET /api/v1/videos/{id}/thumbnail)
  - Location: `src/stoat_ferret/api/routers/videos.py:109`

- `async get_video(video_id: str, repo: RepoDep) -> VideoResponse`
  - Description: Get video by ID (GET /api/v1/videos/{id})
  - Location: `src/stoat_ferret/api/routers/videos.py:142`

- `async scan_videos(scan_request: ScanRequest, request: Request) -> JobSubmitResponse`
  - Description: Submit directory scan as async job with path validation (POST /api/v1/videos/scan)
  - Location: `src/stoat_ferret/api/routers/videos.py:168`

- `async delete_video(video_id: str, repo: RepoDep, delete_file: bool) -> Response`
  - Description: Delete video from library, optionally removing source file (DELETE /api/v1/videos/{id})
  - Location: `src/stoat_ferret/api/routers/videos.py:211`

#### projects.py

- `async get_project_repository(request: Request) -> AsyncProjectRepository`
  - Description: FastAPI dependency -- get project repository from app state
  - Location: `src/stoat_ferret/api/routers/projects.py:34`

- `async get_clip_repository(request: Request) -> AsyncClipRepository`
  - Description: FastAPI dependency -- get clip repository from app state
  - Location: `src/stoat_ferret/api/routers/projects.py:52`

- `async get_video_repository(request: Request) -> AsyncVideoRepository`
  - Description: FastAPI dependency -- get video repository from app state
  - Location: `src/stoat_ferret/api/routers/projects.py:70`

- `async list_projects(repo: ProjectRepoDep, limit: int, offset: int) -> ProjectListResponse`
  - Description: List all projects with pagination (GET /api/v1/projects)
  - Location: `src/stoat_ferret/api/routers/projects.py:97`

- `async create_project(project_data: ProjectCreate, request: Request, repo: ProjectRepoDep) -> ProjectResponse`
  - Description: Create a new project with WebSocket broadcast (POST /api/v1/projects)
  - Location: `src/stoat_ferret/api/routers/projects.py:121`

- `async get_project(project_id: str, repo: ProjectRepoDep) -> ProjectResponse`
  - Description: Get project by ID (GET /api/v1/projects/{id})
  - Location: `src/stoat_ferret/api/routers/projects.py:161`

- `async delete_project(project_id: str, repo: ProjectRepoDep) -> Response`
  - Description: Delete project (DELETE /api/v1/projects/{id})
  - Location: `src/stoat_ferret/api/routers/projects.py:187`

- `async list_clips(project_id: str, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> ClipListResponse`
  - Description: List clips in project (GET /api/v1/projects/{id}/clips)
  - Location: `src/stoat_ferret/api/routers/projects.py:213`

- `async add_clip(project_id: str, request: ClipCreate, ...) -> ClipResponse`
  - Description: Add clip to project with Rust validation (POST /api/v1/projects/{id}/clips)
  - Location: `src/stoat_ferret/api/routers/projects.py:248`

- `async update_clip(project_id: str, clip_id: str, request: ClipUpdate, ...) -> ClipResponse`
  - Description: Update clip with Rust validation (PATCH /api/v1/projects/{id}/clips/{clip_id})
  - Location: `src/stoat_ferret/api/routers/projects.py:314`

- `async delete_clip(project_id: str, clip_id: str, clip_repo: ClipRepoDep) -> Response`
  - Description: Delete clip (DELETE /api/v1/projects/{id}/clips/{clip_id})
  - Location: `src/stoat_ferret/api/routers/projects.py:386`

#### effects.py

- `async get_effect_registry(request: Request) -> EffectRegistry`
  - Description: FastAPI dependency -- get effect registry from app state with default fallback
  - Location: `src/stoat_ferret/api/routers/effects.py:50`

- `async list_effects(registry: RegistryDep) -> EffectListResponse`
  - Description: List all available effects with metadata, schemas, and previews (GET /api/v1/effects)
  - Location: `src/stoat_ferret/api/routers/effects.py:94`

- `async preview_effect(request: EffectPreviewRequest, registry: RegistryDep) -> EffectPreviewResponse`
  - Description: Preview the filter string without applying (POST /api/v1/effects/preview)
  - Location: `src/stoat_ferret/api/routers/effects.py:117`

- `async apply_effect_to_clip(project_id: str, clip_id: str, request: EffectApplyRequest, ...) -> EffectApplyResponse`
  - Description: Apply an effect to a clip with validation (POST /api/v1/projects/{id}/clips/{id}/effects)
  - Location: `src/stoat_ferret/api/routers/effects.py:180`

- `async update_clip_effect(project_id: str, clip_id: str, index: int, request: EffectUpdateRequest, ...) -> EffectApplyResponse`
  - Description: Update effect at index on a clip (PATCH /api/v1/projects/{id}/clips/{id}/effects/{index})
  - Location: `src/stoat_ferret/api/routers/effects.py:293`

- `async delete_clip_effect(project_id: str, clip_id: str, index: int, ...) -> EffectDeleteResponse`
  - Description: Remove effect at index from a clip (DELETE /api/v1/projects/{id}/clips/{id}/effects/{index})
  - Location: `src/stoat_ferret/api/routers/effects.py:411`

- `async apply_transition(project_id: str, request: TransitionRequest, ...) -> TransitionResponse`
  - Description: Apply transition between adjacent clips with adjacency validation (POST /api/v1/projects/{id}/effects/transition)
  - Location: `src/stoat_ferret/api/routers/effects.py:483`

#### jobs.py

- `async get_job_status(job_id: str, request: Request) -> JobStatusResponse`
  - Description: Get status of a submitted job (GET /api/v1/jobs/{id})
  - Location: `src/stoat_ferret/api/routers/jobs.py:13`

- `async cancel_job(job_id: str, request: Request) -> JobStatusResponse`
  - Description: Request cancellation of a job, returns 409 if already terminal (POST /api/v1/jobs/{id}/cancel)
  - Location: `src/stoat_ferret/api/routers/jobs.py:51`

#### filesystem.py

- `_list_dirs(path: str) -> list[DirectoryEntry]`
  - Description: List subdirectories within a path using os.scandir, skipping hidden dirs
  - Location: `src/stoat_ferret/api/routers/filesystem.py:18`
  - Dependencies: `os.scandir`, `pathlib.Path`

- `async list_directories(path: str | None) -> DirectoryListResponse`
  - Description: List subdirectories within a path with scan root validation (GET /api/v1/filesystem/directories)
  - Location: `src/stoat_ferret/api/routers/filesystem.py:42`
  - Dependencies: `validate_scan_path`, `get_settings`, `asyncio.run_in_executor`

#### ws.py

- `async _heartbeat_loop(ws: WebSocket, interval: float) -> None`
  - Description: Send periodic heartbeat messages to keep the WebSocket connection alive
  - Location: `src/stoat_ferret/api/routers/ws.py:17`
  - Dependencies: `asyncio`, `EventType.HEARTBEAT`, `build_event`

- `async websocket_endpoint(websocket: WebSocket) -> None`
  - Description: Handle WebSocket connections at /ws with configurable heartbeat interval
  - Location: `src/stoat_ferret/api/routers/ws.py:29`
  - Dependencies: `ConnectionManager`, `get_settings`

### Module-Level Variables

#### effects.py

- `effect_applications_total` -- Prometheus Counter for effect applications by type
- `transition_applications_total` -- Prometheus Counter for transition applications by type

## Dependencies

### Internal Dependencies
- `stoat_ferret.api.schemas` -- Request/response Pydantic models (video, project, clip, job, effect, filesystem)
- `stoat_ferret.api.services.scan` -- Scan path validation, job type constant
- `stoat_ferret.api.settings` -- Application settings
- `stoat_ferret.api.websocket` -- ConnectionManager, EventType, build_event
- `stoat_ferret.db` -- Repository protocols and implementations, models
- `stoat_ferret.effects.definitions` -- create_default_registry
- `stoat_ferret.effects.registry` -- EffectRegistry

### External Dependencies
- `fastapi` -- APIRouter, Request, Response, HTTPException, Depends, Query, FileResponse
- `starlette` -- WebSocket, WebSocketDisconnect
- `structlog` -- Structured logging
- `prometheus_client` -- Counter for metrics

## Relationships

```mermaid
---
title: Code Diagram for API Routers
---
flowchart TB
    subgraph Routers
        health[health.py<br/>GET /health/live<br/>GET /health/ready]
        videos[videos.py<br/>GET/POST/DELETE /api/v1/videos<br/>GET .../search<br/>GET .../thumbnail]
        projects[projects.py<br/>CRUD /api/v1/projects<br/>CRUD .../clips]
        effects[effects.py<br/>GET /api/v1/effects<br/>POST .../effects/preview<br/>CRUD .../clips/{id}/effects<br/>POST .../effects/transition]
        jobs[jobs.py<br/>GET /api/v1/jobs/{id}<br/>POST .../cancel]
        filesystem[filesystem.py<br/>GET /api/v1/filesystem/directories]
        ws[ws.py<br/>WS /ws]
    end

    subgraph Dependencies
        schemas[api/schemas]
        services[api/services]
        settings[api/settings]
        db[db repositories]
        websocket[api/websocket]
        registry[effects.registry]
    end

    videos --> schemas
    videos --> services
    videos --> settings
    videos --> db
    projects --> schemas
    projects --> db
    projects --> websocket
    effects --> schemas
    effects --> db
    effects --> registry
    jobs --> schemas
    filesystem --> schemas
    filesystem --> services
    filesystem --> settings
    ws --> websocket
    ws --> settings
    health --> db
```
