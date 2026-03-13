# API Gateway

## Purpose

The API Gateway component is the primary HTTP entry point for the stoat-and-ferret backend. It exposes a versioned REST API and a WebSocket endpoint, routes requests to the appropriate domain logic, enforces middleware policies for observability and tracing, and manages the full lifecycle of infrastructure dependencies including the database, job queue, FFmpeg executor, and WebSocket connection manager.

## Responsibilities

- Accept and route HTTP requests across all domain areas: videos, projects, clips, effects, composition, audio, timeline, batch rendering, and version history
- Enforce per-request correlation ID generation and Prometheus metrics collection via middleware
- Manage application lifecycle: database initialization, job queue startup, audit logger creation, and graceful shutdown
- Serve the React SPA as static files with a catch-all fallback route for client-side routing (FR-003)
- Broadcast real-time WebSocket events to all connected clients when state changes occur
- Delegate compute-intensive operations to the Rust Core component via PyO3 bindings
- Validate request parameters and translate domain errors into structured HTTP error responses
- Submit long-running operations (directory scans, batch renders) as background jobs via the Job Queue component

## Interfaces

### Provided Interfaces

**REST API (HTTP/JSON)**

| Domain | Endpoints | Methods |
|--------|-----------|---------|
| Health | `/health/live`, `/health/ready` | GET |
| Videos | `/api/v1/videos`, `/api/v1/videos/search`, `/api/v1/videos/{id}`, `/api/v1/videos/{id}/thumbnail`, `/api/v1/videos/scan` | GET, POST, DELETE |
| Projects | `/api/v1/projects`, `/api/v1/projects/{id}`, `/api/v1/projects/{id}/clips`, `/api/v1/projects/{id}/clips/{clip_id}` | GET, POST, PATCH, DELETE |
| Jobs | `/api/v1/jobs/{id}`, `/api/v1/jobs/{id}/cancel` | GET, POST |
| Effects | `/api/v1/effects`, `/api/v1/effects/preview`, `/api/v1/projects/{id}/clips/{clip_id}/effects`, `/api/v1/projects/{id}/clips/{clip_id}/effects/{index}`, `/api/v1/projects/{id}/effects/transition` | GET, POST, PATCH, DELETE |
| Compose | `/api/v1/compose/presets`, `/api/v1/projects/{id}/compose/layout` | GET, POST |
| Audio | `/api/v1/projects/{id}/audio/mix`, `/api/v1/audio/mix/preview` | PUT, POST |
| Filesystem | `/api/v1/filesystem/directories` | GET |
| Timeline | `/api/v1/projects/{id}/timeline`, `/api/v1/projects/{id}/timeline/clips`, `/api/v1/projects/{id}/timeline/clips/{clip_id}`, `/api/v1/projects/{id}/timeline/transitions`, `/api/v1/projects/{id}/timeline/transitions/{transition_id}` | GET, PUT, POST, PATCH, DELETE |
| Batch | `/api/v1/render/batch`, `/api/v1/render/batch/{batch_id}` | GET, POST |
| Versions | `/api/v1/projects/{id}/versions`, `/api/v1/projects/{id}/versions/{version}/restore` | GET, POST |
| SPA | `/gui`, `/gui/{path}` | GET |
| Metrics | `/metrics` | GET (Prometheus text) |

**WebSocket**
- `GET /ws` — Persistent connection for real-time event broadcasting

**WebSocket Events Broadcast**
- `HEALTH_STATUS` — Health or readiness status changes
- `SCAN_STARTED` — Directory scan initiated
- `SCAN_COMPLETED` — Directory scan finished with video count
- `PROJECT_CREATED` — New project created
- `HEARTBEAT` — Periodic keepalive (interval configurable via `STOAT_WS_HEARTBEAT_INTERVAL`)
- `TIMELINE_UPDATED` — Timeline tracks or clips modified (v013+)
- `LAYOUT_APPLIED` — Layout preset applied to a project (v014+)
- `AUDIO_MIX_CHANGED` — Audio mix configuration updated (v015+)
- `TRANSITION_APPLIED` — Transition applied between adjacent clips (v016+)

**HTTP Response Headers**
- `X-Correlation-ID` — Unique request identifier on every response

### Required Interfaces

- **Data Access component** — All repository protocols: `AsyncVideoRepository`, `AsyncProjectRepository`, `AsyncClipRepository`, `AsyncTimelineRepository`, `AsyncVersionRepository`, `AuditLogger`
- **Rust Core component** — Clip validation, layout computation, composition graph building, audio filter generation, transition calculation, batch progress aggregation
- **FFmpeg Integration component** — `ObservableFFmpegExecutor` for thumbnail generation; `ffprobe_video()` for metadata extraction during directory scans
- **Effects Engine component** — `EffectRegistry` for effect discovery, parameter validation, and filter string generation
- **Job Queue component** — `AsyncioJobQueue` for submitting and tracking background scan and render jobs

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Application Factory | `src/stoat_ferret/api/app.py` | `create_app()` factory, lifespan management, DI wiring, router inclusion, middleware stack |
| Entry Point | `src/stoat_ferret/api/__main__.py` | Uvicorn server startup driven by settings |
| Settings | `src/stoat_ferret/api/settings.py` | Pydantic settings model with STOAT_ environment variable prefix |
| Correlation Middleware | `src/stoat_ferret/api/middleware/correlation.py` | Per-request X-Correlation-ID generation and context storage |
| Metrics Middleware | `src/stoat_ferret/api/middleware/metrics.py` | Prometheus request count and duration histograms |
| Router: Videos | `src/stoat_ferret/api/routers/videos.py` | Video listing, search, thumbnail serving, async scan submission, deletion |
| Router: Projects | `src/stoat_ferret/api/routers/projects.py` | Project CRUD, clip management, PROJECT_CREATED broadcast |
| Router: Jobs | `src/stoat_ferret/api/routers/jobs.py` | Background job status polling and cancellation |
| Router: Effects | `src/stoat_ferret/api/routers/effects.py` | Effect catalog, preview, apply, update, delete, transition application |
| Router: Compose | `src/stoat_ferret/api/routers/compose.py` | Layout preset listing, preset/custom layout application, LAYOUT_APPLIED broadcast |
| Router: Audio | `src/stoat_ferret/api/routers/audio.py` | Audio mix configuration and stateless preview, AUDIO_MIX_CHANGED broadcast |
| Router: Filesystem | `src/stoat_ferret/api/routers/filesystem.py` | Directory browsing with allowed-root security validation |
| Router: Timeline | `src/stoat_ferret/api/routers/timeline.py` | Track management, clip positioning, transitions, TIMELINE_UPDATED and TRANSITION_APPLIED broadcasts |
| Router: Batch | `src/stoat_ferret/api/routers/batch.py` | Batch render submission, semaphore-limited concurrency, aggregated progress |
| Router: Versions | `src/stoat_ferret/api/routers/versions.py` | Project version listing with pagination, non-destructive version restoration |
| Router: Health | `src/stoat_ferret/api/routers/health.py` | Liveness probe, readiness probe with database and FFmpeg checks |
| Router: WebSocket | `src/stoat_ferret/api/routers/ws.py` | WebSocket endpoint, heartbeat loop, graceful disconnection |
| WebSocket Manager | `src/stoat_ferret/api/websocket/manager.py` | `ConnectionManager` — set-based connection tracking, thread-safe broadcast with dead-connection cleanup |
| WebSocket Events | `src/stoat_ferret/api/websocket/events.py` | `EventType` enum, `build_event()` helper with correlation ID and ISO timestamp |
| Scan Service | `src/stoat_ferret/api/services/scan.py` | Directory walking, ffprobe metadata extraction, thumbnail generation, progress/cancellation, WebSocket events |
| Thumbnail Service | `src/stoat_ferret/api/services/thumbnail.py` | FFmpeg frame extraction at 5-second offset, JPEG output |
| Schemas | `src/stoat_ferret/api/schemas/` | Pydantic request/response models for all domains (Video, Project, Clip, Job, Effect, Audio, Batch, Compose, Timeline, Version, Filesystem) |

## Key Behaviors

**Dependency Injection (FR-004):** All stateful dependencies (repositories, FFmpeg executor, job queue, WebSocket manager, audit logger) are stored on `app.state` and created during the lifespan startup phase. Tests inject mock implementations by pre-setting `app.state._deps_injected = True`, which suppresses the lifespan setup.

**SPA Catch-All (FR-003):** When `gui_static_path` is configured, `GET /gui/{path}` serves the requested static file if it exists on disk; otherwise it returns `index.html`, enabling React Router to handle client-side navigation.

**Async Scan Pattern:** `POST /api/v1/videos/scan` returns 202 Accepted with a `job_id` immediately. Clients poll `GET /api/v1/jobs/{job_id}` for progress. The scan handler runs as a background asyncio task, broadcasting `SCAN_STARTED` and `SCAN_COMPLETED` events over WebSocket.

**Non-Destructive Versioning:** `POST /api/v1/projects/{id}/versions/{version}/restore` creates a new version containing the restored timeline data rather than overwriting the current state, preserving full edit history.

**Concurrency Control (Batch):** Batch render jobs use `asyncio.Semaphore(batch_parallel_limit)` to cap concurrent renders. The default limit is 4, configurable via `STOAT_BATCH_PARALLEL_LIMIT`.

**Path Security:** The filesystem and scan endpoints validate that requested paths fall within the `allowed_scan_roots` setting. An empty `allowed_scan_roots` list permits all paths.

## Inter-Component Relationships

```
Web GUI
    |
    | HTTP/JSON, WebSocket
    v
API Gateway
    |-- reads/writes --> Data Access (all repository operations)
    |-- calls --> Rust Core (clip validate, layout, composition, audio, batch progress)
    |-- calls --> FFmpeg Integration (thumbnail generation, video probe)
    |-- delegates jobs --> Job Queue (scan, batch render)
    |-- looks up effects --> Effects Engine (registry, filter strings)
```

## Version History

| Version | Changes |
|---------|---------|
| v012 | Added `router-compose.md` (compose router, layout presets); added `router-audio.md` (audio mix endpoints) |
| v013 | Added `router-timeline.md` (timeline tracks and clip positioning); added `TIMELINE_UPDATED` WebSocket event |
| v014 | Added `LAYOUT_APPLIED` WebSocket event broadcast from compose router |
| v015 | Added `AUDIO_MIX_CHANGED` WebSocket event broadcast from audio router |
| v016 | Added `router-versions.md` (version listing, non-destructive restore); added `TRANSITION_APPLIED` WebSocket event from timeline router |
| v017 | Added `router-batch.md` (batch render submission and progress tracking) |
