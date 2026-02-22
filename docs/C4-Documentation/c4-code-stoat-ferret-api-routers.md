# C4 Code Level: API Routers

## Overview
- **Name**: API Routers
- **Description**: FastAPI route handlers for health, videos, projects, clips, jobs, effects, transitions, and WebSocket endpoints
- **Location**: `src/stoat_ferret/api/routers/`
- **Language**: Python (async/await)
- **Purpose**: Define all REST API and WebSocket endpoints, map HTTP requests to business logic via dependency injection
- **Parent Component**: [API Gateway](./c4-component-api-gateway.md)

## Code Elements

### Functions/Methods

#### health.py

- `async liveness() -> dict[str, str]`
  - Description: Liveness probe -- returns 200 if the server is running (GET /health/live)
  - Location: `src/stoat_ferret/api/routers/health.py:17`
  - Dependencies: None

- `async readiness(request: Request) -> JSONResponse`
  - Description: Readiness probe -- checks database and FFmpeg availability (GET /health/ready)
  - Location: `src/stoat_ferret/api/routers/health.py:30`
  - Dependencies: `_check_database`, `_check_ffmpeg`

- `async _check_database(request: Request) -> dict[str, Any]`
  - Description: Check database connectivity with latency measurement
  - Location: `src/stoat_ferret/api/routers/health.py:63`
  - Dependencies: `app.state.db`

- `_check_ffmpeg() -> dict[str, Any]`
  - Description: Check FFmpeg availability by running ffmpeg -version
  - Location: `src/stoat_ferret/api/routers/health.py:85`
  - Dependencies: `subprocess`, `shutil`

#### videos.py

- `async get_repository(request: Request) -> AsyncVideoRepository`
  - Description: FastAPI dependency -- get video repository from app state
  - Location: `src/stoat_ferret/api/routers/videos.py:34`

- `async list_videos(repo, limit, offset) -> VideoListResponse`
  - Description: List videos with pagination (GET /api/v1/videos)
  - Location: `src/stoat_ferret/api/routers/videos.py:57`

- `async search_videos(repo, q, limit) -> VideoSearchResponse`
  - Description: Search videos by filename or path (GET /api/v1/videos/search)
  - Location: `src/stoat_ferret/api/routers/videos.py:84`

- `async get_thumbnail(video_id, repo) -> FileResponse`
  - Description: Get thumbnail image for a video (GET /api/v1/videos/{id}/thumbnail)
  - Location: `src/stoat_ferret/api/routers/videos.py:109`

- `async get_video(video_id, repo) -> VideoResponse`
  - Description: Get video by ID (GET /api/v1/videos/{id})
  - Location: `src/stoat_ferret/api/routers/videos.py:142`

- `async scan_videos(scan_request, request) -> JobSubmitResponse`
  - Description: Submit directory scan as async job (POST /api/v1/videos/scan)
  - Location: `src/stoat_ferret/api/routers/videos.py:168`

- `async delete_video(video_id, repo, delete_file) -> Response`
  - Description: Delete video from library (DELETE /api/v1/videos/{id})
  - Location: `src/stoat_ferret/api/routers/videos.py:211`

#### projects.py

- `async list_projects(repo, limit, offset) -> ProjectListResponse`
  - Description: List all projects (GET /api/v1/projects)
  - Location: `src/stoat_ferret/api/routers/projects.py:95`

- `async create_project(request, repo) -> ProjectResponse`
  - Description: Create a new project (POST /api/v1/projects)
  - Location: `src/stoat_ferret/api/routers/projects.py:118`

- `async get_project(project_id, repo) -> ProjectResponse`
  - Description: Get project by ID (GET /api/v1/projects/{id})
  - Location: `src/stoat_ferret/api/routers/projects.py:146`

- `async delete_project(project_id, repo) -> Response`
  - Description: Delete project (DELETE /api/v1/projects/{id})
  - Location: `src/stoat_ferret/api/routers/projects.py:172`

- `async list_clips(project_id, project_repo, clip_repo) -> ClipListResponse`
  - Description: List clips in project (GET /api/v1/projects/{id}/clips)
  - Location: `src/stoat_ferret/api/routers/projects.py:198`

- `async add_clip(project_id, request, ...) -> ClipResponse`
  - Description: Add clip to project with Rust validation (POST /api/v1/projects/{id}/clips)
  - Location: `src/stoat_ferret/api/routers/projects.py:233`

- `async update_clip(project_id, clip_id, request, ...) -> ClipResponse`
  - Description: Update clip with Rust validation (PATCH /api/v1/projects/{id}/clips/{clip_id})
  - Location: `src/stoat_ferret/api/routers/projects.py:299`

- `async delete_clip(project_id, clip_id, clip_repo) -> Response`
  - Description: Delete clip (DELETE /api/v1/projects/{id}/clips/{clip_id})
  - Location: `src/stoat_ferret/api/routers/projects.py:371`

#### effects.py

- `async get_effect_registry(request: Request) -> EffectRegistry`
  - Description: FastAPI dependency -- get effect registry from app state, falls back to default registry
  - Location: `src/stoat_ferret/api/routers/effects.py:50`

- `async list_effects(registry) -> EffectListResponse`
  - Description: List all available effects with metadata, schemas, and previews (GET /api/v1/effects)
  - Location: `src/stoat_ferret/api/routers/effects.py:94`

- `async preview_effect(request, registry) -> EffectPreviewResponse`
  - Description: Preview the filter string without applying (POST /api/v1/effects/preview)
  - Location: `src/stoat_ferret/api/routers/effects.py:117`

- `async apply_effect_to_clip(project_id, clip_id, request, ...) -> EffectApplyResponse`
  - Description: Apply an effect to a clip (POST /api/v1/projects/{id}/clips/{id}/effects)
  - Location: `src/stoat_ferret/api/routers/effects.py:180`

- `async update_clip_effect(project_id, clip_id, index, request, ...) -> EffectApplyResponse`
  - Description: Update effect at index on a clip (PATCH /api/v1/projects/{id}/clips/{id}/effects/{index})
  - Location: `src/stoat_ferret/api/routers/effects.py:293`

- `async delete_clip_effect(project_id, clip_id, index, ...) -> EffectDeleteResponse`
  - Description: Remove effect at index from a clip (DELETE /api/v1/projects/{id}/clips/{id}/effects/{index})
  - Location: `src/stoat_ferret/api/routers/effects.py:411`

- `async apply_transition(project_id, request, ...) -> TransitionResponse`
  - Description: Apply transition between adjacent clips (POST /api/v1/projects/{id}/effects/transition)
  - Location: `src/stoat_ferret/api/routers/effects.py:483`

#### jobs.py

- `async get_job_status(job_id, request) -> JobStatusResponse`
  - Description: Get status of a submitted job (GET /api/v1/jobs/{id})
  - Location: `src/stoat_ferret/api/routers/jobs.py:13`

#### ws.py

- `async _heartbeat_loop(ws: WebSocket, interval: float) -> None`
  - Description: Send periodic heartbeat messages to keep the connection alive
  - Location: `src/stoat_ferret/api/routers/ws.py:17`
  - Dependencies: `asyncio`, `EventType.HEARTBEAT`, `build_event`

- `async websocket_endpoint(websocket: WebSocket) -> None`
  - Description: Handle WebSocket connections at /ws with configurable heartbeat interval. Accepts the connection, starts a heartbeat task, and listens for incoming messages until disconnect.
  - Location: `src/stoat_ferret/api/routers/ws.py:29`
  - Dependencies: `ConnectionManager`, `get_settings`, `ws_heartbeat_interval`

### Module-Level Variables

#### effects.py

- `effect_applications_total` -- Prometheus Counter for effect applications by type
- `transition_applications_total` -- Prometheus Counter for transition applications by type

## Dependencies

### Internal Dependencies
- `stoat_ferret.api.schemas` -- Request/response Pydantic models (video, project, clip, job, effect)
- `stoat_ferret.api.services.scan` -- Scan path validation, job type constant
- `stoat_ferret.api.settings` -- Application settings
- `stoat_ferret.api.websocket` -- ConnectionManager, EventType, build_event
- `stoat_ferret.db` -- Repository protocols and implementations, models
- `stoat_ferret.effects.definitions` -- create_default_registry
- `stoat_ferret.effects.registry` -- EffectRegistry

### External Dependencies
- `fastapi` -- APIRouter, Request, Response, HTTPException, Depends, Query
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
        videos[videos.py<br/>GET/POST/DELETE /api/v1/videos<br/>GET /api/v1/videos/search<br/>GET /api/v1/videos/{id}/thumbnail]
        projects[projects.py<br/>CRUD /api/v1/projects<br/>CRUD .../clips]
        effects[effects.py<br/>GET /api/v1/effects<br/>POST .../effects/preview<br/>CRUD .../clips/{id}/effects<br/>POST .../effects/transition]
        jobs[jobs.py<br/>GET /api/v1/jobs/{id}]
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
    effects --> schemas
    effects --> db
    effects --> registry
    jobs --> schemas
    ws --> websocket
    health --> db
```
