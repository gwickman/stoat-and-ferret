# Container Interfaces

Detailed interface documentation for inter-container communication in stoat-and-ferret.

## API Server → External Clients

### REST API (HTTP/JSON, port 8765)

The API Server exposes a versioned REST API under `/api/v1/` with the following domain groups:

| Domain | Base Path | Key Operations |
|--------|-----------|---------------|
| Health | `/health/` | Liveness probe, readiness probe (DB + FFmpeg + degraded checks for preview/proxy/render) |
| Videos | `/api/v1/videos` | List, search (FTS5), get, delete, thumbnail, scan |
| Projects | `/api/v1/projects` | CRUD, clip management within projects |
| Jobs | `/api/v1/jobs` | Background job status polling and cancellation |
| Effects | `/api/v1/effects` | Effect catalog, preview, thumbnail preview, apply/update/delete, transitions |
| Compose | `/api/v1/compose` | Layout presets (with positions field for custom coordinates), apply layout to project |
| Audio | `/api/v1/projects/{id}/audio` | Audio mix configuration and stateless preview |
| Timeline | `/api/v1/projects/{id}/timeline` | Track CRUD, clip positioning, transition application |
| Batch | `/api/v1/render/batch` | Batch render submission and progress tracking |
| Versions | `/api/v1/projects/{id}/versions` | Version listing (GET), version creation (POST), non-destructive restore |
| Preview | `/api/v1/preview` | HLS preview session lifecycle: start, status, seek, stop, manifest, segments, cache |
| Proxy | `/api/v1/videos/{id}/proxy`, `/api/v1/proxy/batch` | Single and batch proxy generation, status, deletion |
| Thumbnails | `/api/v1/videos/{id}/thumbnails` | Thumbnail sprite strip generation, metadata, JPEG serving |
| Waveform | `/api/v1/videos/{id}/waveform` | Waveform generation (PNG/JSON), metadata, file serving |
| Filesystem | `/api/v1/filesystem` | Directory browsing with pagination (`limit`, `offset`, `path` query params) |
| Render | `/api/v1/render` | Render job lifecycle (submit, query, cancel, retry, delete), encoder detection/refresh, format listing, queue status |
| Metrics | `/metrics` | Prometheus text exposition format |
| SPA | `/gui` | Static file serving with catch-all for client-side routing |

**Cross-cutting headers:**
- `X-Correlation-ID` — unique identifier on every response for request tracing

### WebSocket (port 8765, path `/ws`)

Persistent connection for real-time server-to-client event broadcasting.

**Event format:**
```json
{
  "type": "EVENT_TYPE",
  "data": { ... },
  "correlation_id": "uuid",
  "timestamp": "ISO 8601"
}
```

**Events (25 types):**

| Event | Trigger | Data |
|-------|---------|------|
| `HEARTBEAT` | Periodic (configurable interval) | `{}` |
| `HEALTH_STATUS` | Health/readiness status change | Status details |
| `SCAN_STARTED` | `POST /api/v1/videos/scan` | Job ID, directory path |
| `SCAN_COMPLETED` | Scan job finishes | Video count, job ID |
| `PROJECT_CREATED` | `POST /api/v1/projects` | Project ID, name |
| `TIMELINE_UPDATED` | Timeline track/clip mutation | Project ID |
| `LAYOUT_APPLIED` | `POST /api/v1/projects/{id}/compose/layout` | Project ID, preset name |
| `AUDIO_MIX_CHANGED` | `PUT /api/v1/projects/{id}/audio/mix` | Project ID |
| `TRANSITION_APPLIED` | Transition applied between clips | Project ID, transition type |
| `JOB_PROGRESS` | Background job progress update | Job ID, progress (0.0–1.0) |
| `PREVIEW_GENERATING` | Preview session generation started | Session ID, project ID |
| `PREVIEW_READY` | Preview session ready for playback | Session ID, manifest URL |
| `PREVIEW_SEEKING` | Preview session seek in progress | Session ID, position |
| `PREVIEW_ERROR` | Preview session error | Session ID, error message |
| `AI_ACTION` | AI-driven action notification | Action type, details |
| `RENDER_QUEUED` | Render job submitted and queued | Job ID, project ID |
| `RENDER_STARTED` | Render job execution started | Job ID |
| `RENDER_PROGRESS` | Render progress (throttled: 0.5s + 5% delta) | Job ID, progress (0.0–1.0) |
| `RENDER_FRAME_AVAILABLE` | Render frame preview available (max 2/s) | Job ID, frame data (540p JPEG) |
| `RENDER_COMPLETED` | Render job finished successfully | Job ID, output path |
| `RENDER_FAILED` | Render job failed permanently | Job ID, error message |
| `RENDER_CANCELLED` | Render job cancelled by user | Job ID |
| `RENDER_QUEUE_STATUS` | Queue capacity snapshot | Active jobs, pending jobs, max concurrent |
| `PROXY_READY` | Proxy video generation complete | Video ID, proxy quality |

All events are actively wired — they are emitted by their respective routers and services during real API operations, not just defined.

## API Server → SQLite Database

| Interface | Technology | Details |
|-----------|-----------|---------|
| Async queries | `aiosqlite` | Non-blocking reads/writes via async context managers |
| Schema init | `create_tables_async()` | Idempotent DDL with backward-compatible `ALTER TABLE ADD COLUMN` migrations |
| FTS5 search | SQLite triggers | `videos_fts` virtual table synced automatically on insert/update/delete |
| Foreign keys | `PRAGMA foreign_keys = ON` | Cascade delete (project → clips, tracks, versions); restrict delete (video ← clips) |

## API Server → FFmpeg / FFprobe

| Interface | Technology | Details |
|-----------|-----------|---------|
| FFmpeg execution (sync) | `subprocess.run()` | Synchronous subprocess for encoding and thumbnail generation |
| FFmpeg execution (async) | `asyncio.create_subprocess_exec()` | Async subprocess for proxy transcoding and HLS generation with real-time progress tracking and cooperative cancellation |
| FFprobe metadata | `asyncio.create_subprocess_exec()` | Async subprocess with 30s timeout; JSON output parsing |
| Observable wrapper | `ObservableFFmpegExecutor` | Structured logging (started/completed/failed events) and Prometheus metrics (count, duration, active gauge) |
| Render execution | `asyncio.create_subprocess_exec()` | Async subprocess for render job FFmpeg execution with stdin-based cancellation, real-time progress parsing via Rust bindings, speed ratio tracking |
| Health check | Binary availability probe | Readiness endpoint checks FFmpeg binary exists and is executable; non-critical (degraded only, LRN-136) |

## Web GUI → API Server

| Interface | Technology | Details |
|-----------|-----------|---------|
| REST calls | `fetch()` | All data operations via HTTP/JSON to `/api/v1/*` endpoints |
| WebSocket | `WebSocket` API | Persistent connection to `/ws` with exponential-backoff reconnect (1s–30s); receives 25 event types |
| Health polling | `GET /health/ready` | 30-second interval polling from Dashboard page; displays degraded status |
| Metrics polling | `GET /metrics` | 30-second interval polling; Prometheus text format parsed client-side |
| Job polling | `GET /api/v1/jobs/{id}` | 1-second interval polling from ScanModal until terminal state |
| Preview streaming | HLS manifest + segments | `GET /api/v1/preview/{session}/manifest.m3u8` + segments via HLS.js or native `<video>` |
| Proxy status | `GET /api/v1/videos/{id}/proxy` | Proxy status checked for video cards; updates via PROXY_READY WebSocket event |
| Waveform images | `GET /api/v1/videos/{id}/waveform.png` | PNG waveform loaded as CSS background-image in AudioWaveform component |

## Version History

| Version | Changes |
|---------|---------|
| v018 | Initial Container interfaces documentation |
| v027 | Added preview, proxy, thumbnails, waveform API domains; expanded WebSocket events to 17; added async FFmpeg execution; added filesystem pagination; documented degraded health semantics; added Web GUI preview streaming and proxy status interfaces |
| v029 | Added render API domain (job lifecycle, encoders, formats, queue status); expanded WebSocket events to 25 (8 render events); added render FFmpeg execution interface; updated health check for render subsystem |
