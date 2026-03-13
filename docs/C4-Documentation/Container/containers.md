# Container Diagram

Overview of stoat-and-ferret deployment containers and their interactions.

## Containers

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User / AI Agent                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
            HTTP/JSON (port 8765) + WebSocket (/ws)
                                │
┌───────────────────────────────┴─────────────────────────────────────┐
│                     API Server (Python/FastAPI)                      │
│                                                                     │
│  Components:                                                        │
│    API Gateway  │  Data Access  │  Effects Engine                    │
│    FFmpeg Integration  │  Job Queue  │  Observability                │
│                                                                     │
│  Embedded via PyO3:                                                 │
│    Rust Core (stoat_ferret_core native extension)                   │
│                                                                     │
│  Serves SPA at /gui (static files from gui/dist/)                   │
│  Exposes Prometheus metrics at /metrics                             │
└───────┬───────────────┬───────────────┬─────────────────────────────┘
        │               │               │
        │ subprocess    │ aiosqlite     │ static files
        │               │               │
┌───────┴───────┐ ┌─────┴──────┐ ┌─────┴──────────────────────────────┐
│  FFmpeg /     │ │  SQLite    │ │  Web GUI (React SPA)                │
│  FFprobe      │ │  Database  │ │                                     │
│  (external)   │ │            │ │  Runs in browser; served from       │
│               │ │  data/     │ │  /gui by the API Server             │
│               │ │  stoat.db  │ │                                     │
└───────────────┘ └────────────┘ └─────────────────────────────────────┘
```

## Container Descriptions

### API Server

| Property | Value |
|----------|-------|
| Technology | Python 3.10+, FastAPI, Uvicorn |
| Port | 8765 (configurable via `STOAT_API_PORT`) |
| Role | Primary backend process hosting all server-side logic |

The API Server is a single Uvicorn process running a FastAPI application. It contains six Python components (API Gateway, Data Access, Effects Engine, FFmpeg Integration, Job Queue, Observability) and embeds the Rust Core native extension via PyO3. All dependencies are wired via constructor injection on `app.state` during the lifespan startup phase.

**Hosted Components:**

| Component | Responsibility |
|-----------|---------------|
| API Gateway | HTTP routing, middleware, WebSocket management, SPA serving |
| Data Access | SQLite repository layer (videos, projects, clips, timeline, versions, audit) |
| Effects Engine | Effect catalog, JSON Schema parameter validation, FFmpeg filter string generation |
| FFmpeg Integration | Subprocess execution, metadata extraction (ffprobe), Prometheus metrics |
| Job Queue | Async background job dispatch for scan and batch render operations |
| Observability | Structured logging (structlog), rotating file handler, log format selection |
| Rust Core | Native extension (PyO3): timeline math, clip validation, filter builders, layout engine, composition, batch progress, sanitization |

**Key Capabilities (Phase 3 — v009-v017):**

- Timeline management with tracks and clip positioning (v013)
- Layout composition with 7 presets and custom coordinates (v012-v014)
- Audio mixing with per-track volume/pan and preview (v015)
- Transitions between adjacent clips: fade, xfade, acrossfade (v016)
- Non-destructive project versioning with SHA-256 checksums (v016)
- Batch rendering with semaphore-limited concurrency (v017)
- Full-text video search via SQLite FTS5

**WebSocket Events (all actively wired):**

| Event | Source | Status |
|-------|--------|--------|
| `HEALTH_STATUS` | Health router | Active |
| `SCAN_STARTED` | Scan service | Active |
| `SCAN_COMPLETED` | Scan service | Active |
| `PROJECT_CREATED` | Projects router | Active |
| `HEARTBEAT` | WebSocket router | Active |
| `TIMELINE_UPDATED` | Timeline router (v013+) | Active |
| `LAYOUT_APPLIED` | Compose router (v014+) | Active |
| `AUDIO_MIX_CHANGED` | Audio router (v015+) | Active |
| `TRANSITION_APPLIED` | Timeline router (v016+) | Active |

### Web GUI

| Property | Value |
|----------|-------|
| Technology | React 18, TypeScript, Vite, Zustand |
| Deployment | Static files served by API Server at `/gui` |
| Role | Browser-based user interface for the video editor |

The Web GUI is a React SPA built with Vite and deployed as static assets inside the API Server's `/gui` route. It communicates exclusively via HTTP/JSON REST calls and a persistent WebSocket connection to the API Server.

**Pages:**

| Page | Description |
|------|-------------|
| Dashboard | System health, Prometheus metrics display, activity log |
| Library | Video browsing, search, directory scanning with job polling |
| Projects | Project CRUD, clip management |
| Effects | Effect catalog, schema-driven parameter forms, filter preview |
| Timeline | Interactive canvas with tracks, clips, playhead, zoom; layout preset panel with 16:9 preview |

**Key Capabilities (Phase 3):**

- Timeline visualization with canvas-rendered tracks, clips, time ruler, and playhead (v013-v014)
- Layout preset selection with 16:9 visual preview and coordinate editing (v014-v015)
- Real-time WebSocket event display for TIMELINE_UPDATED, LAYOUT_APPLIED, AUDIO_MIX_CHANGED, TRANSITION_APPLIED (v016-v017)

### SQLite Database

| Property | Value |
|----------|-------|
| Technology | SQLite 3 with FTS5 extension |
| Location | `data/stoat.db` (configurable) |
| Role | Persistent storage for all domain entities |

Accessed via `aiosqlite` for non-blocking I/O. Schema is initialized idempotently on startup with backward-compatible column migrations.

**Tables:**

| Table | Purpose |
|-------|---------|
| `videos` | Video library metadata (path, duration, resolution, codecs) |
| `videos_fts` | FTS5 virtual table for prefix search on filename/path |
| `projects` | Project metadata with JSON fields for transitions and audio_mix |
| `clips` | Clip definitions with effects JSON and timeline positioning columns |
| `tracks` | Timeline tracks with z_index ordering |
| `versions` | Project version snapshots with SHA-256 checksums |
| `audit_log` | Append-only audit trail of data mutations |

### FFmpeg / FFprobe

| Property | Value |
|----------|-------|
| Technology | FFmpeg (external binary) |
| Interaction | Subprocess execution via `subprocess.run()` / `asyncio.create_subprocess_exec()` |
| Role | Video encoding, thumbnail generation, metadata extraction |

The API Server invokes FFmpeg and FFprobe as external subprocesses. All interactions are wrapped in the `ObservableFFmpegExecutor` for structured logging and Prometheus metrics. A `RecordingFFmpegExecutor` / `FakeFFmpegExecutor` pair supports deterministic testing without a real FFmpeg binary.

## Container Interactions

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| User / AI Agent | API Server | HTTP/JSON on port 8765 | REST API calls for all domain operations |
| User / AI Agent | API Server | WebSocket on `/ws` | Real-time event broadcast (9 event types) |
| Web GUI (browser) | API Server | HTTP/JSON + WS | SPA ↔ backend communication |
| API Server | SQLite Database | aiosqlite (async file I/O) | Read/write all domain entities |
| API Server | FFmpeg / FFprobe | subprocess (stdin/stdout) | Video processing and metadata extraction |
| API Server | Web GUI (static) | Filesystem read | Serve SPA assets from `gui/dist/` at `/gui` |

## Version History

| Version | Changes |
|---------|---------|
| v018 | Initial Container-level documentation synthesized from Component-level docs |
