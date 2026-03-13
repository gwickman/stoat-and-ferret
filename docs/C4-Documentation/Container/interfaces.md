# Container Interfaces

Detailed interface documentation for inter-container communication in stoat-and-ferret.

## API Server → External Clients

### REST API (HTTP/JSON, port 8765)

The API Server exposes a versioned REST API under `/api/v1/` with the following domain groups:

| Domain | Base Path | Key Operations |
|--------|-----------|---------------|
| Health | `/health/` | Liveness probe, readiness probe (DB + FFmpeg checks) |
| Videos | `/api/v1/videos` | List, search (FTS5), get, delete, thumbnail, scan |
| Projects | `/api/v1/projects` | CRUD, clip management within projects |
| Jobs | `/api/v1/jobs` | Background job status polling and cancellation |
| Effects | `/api/v1/effects` | Effect catalog, preview, apply/update/delete, transitions |
| Compose | `/api/v1/compose` | Layout presets, apply layout to project |
| Audio | `/api/v1/projects/{id}/audio` | Audio mix configuration and stateless preview |
| Timeline | `/api/v1/projects/{id}/timeline` | Track CRUD, clip positioning, transition application |
| Batch | `/api/v1/render/batch` | Batch render submission and progress tracking |
| Versions | `/api/v1/projects/{id}/versions` | Version listing and non-destructive restore |
| Filesystem | `/api/v1/filesystem` | Directory browsing (path-validated) |
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

**Events:**

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

All Phase 3 events (TIMELINE_UPDATED, LAYOUT_APPLIED, AUDIO_MIX_CHANGED, TRANSITION_APPLIED) are actively wired — they are emitted by their respective routers during real API operations, not just defined.

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
| FFmpeg execution | `subprocess.run()` | Synchronous subprocess for encoding and thumbnail generation |
| FFprobe metadata | `asyncio.create_subprocess_exec()` | Async subprocess with 30s timeout; JSON output parsing |
| Observable wrapper | `ObservableFFmpegExecutor` | Structured logging (started/completed/failed events) and Prometheus metrics (count, duration, active gauge) |
| Health check | Binary availability probe | Readiness endpoint checks FFmpeg binary exists and is executable |

## Web GUI → API Server

| Interface | Technology | Details |
|-----------|-----------|---------|
| REST calls | `fetch()` | All data operations via HTTP/JSON to `/api/v1/*` endpoints |
| WebSocket | `WebSocket` API | Persistent connection to `/ws` with exponential-backoff reconnect (1s–30s) |
| Health polling | `GET /health/ready` | 30-second interval polling from Dashboard page |
| Metrics polling | `GET /metrics` | 30-second interval polling; Prometheus text format parsed client-side |
| Job polling | `GET /api/v1/jobs/{id}` | 1-second interval polling from ScanModal until terminal state |

## Version History

| Version | Changes |
|---------|---------|
| v018 | Initial Container interfaces documentation |
