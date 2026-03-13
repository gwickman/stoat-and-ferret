# Application Factory and Lifespan Management

**Source:** `src/stoat_ferret/api/app.py`
**Component:** API Gateway

## Purpose

Provides the FastAPI application factory (`create_app()`) and lifespan management (`lifespan()`). Orchestrates all router inclusion, middleware setup, dependency injection, WebSocket connection management, and resource lifecycle (database, FFmpeg executor, job queue, audit logging).

## Public Interface

### Functions

- `lifespan(app: FastAPI) -> AsyncGenerator[None, None]`: Async context manager handling startup (database initialization, audit logger setup, job queue creation and worker start) and shutdown (job cancellation, database closure). Skips setup when dependencies are injected for test mode.

- `create_app(video_repository=None, project_repository=None, clip_repository=None, timeline_repository=None, version_repository=None, job_queue=None, ws_manager=None, effect_registry=None, ffmpeg_executor=None, audit_logger=None, gui_static_path=None) -> FastAPI`: Creates and configures the FastAPI application instance with all routers, middleware, metrics endpoint, and optional SPA catch-all routing. Accepts optional dependency injection parameters for testing.

## Key Implementation Details

### Dependency Injection (DI) Wiring

The app supports two modes:

1. **Production mode** (all DI params None): Lifespan creates all dependencies:
   - `app.state.db`: aiosqlite connection to SQLite database
   - `app.state.audit_logger`: AuditLogger with sync connection for change tracking
   - `app.state.ffmpeg_executor`: ObservableFFmpegExecutor wrapping RealFFmpegExecutor for observable FFmpeg command execution
   - `app.state.job_queue`: AsyncioJobQueue with worker task processing async jobs
   - `app.state.ws_manager`: ConnectionManager for WebSocket broadcasting

2. **Test mode** (at least one DI param provided):
   - Sets `app.state._deps_injected = True` to skip lifespan setup
   - Stores provided repositories/managers on `app.state` for route handlers to use
   - Allows tests to inject mocks without database/worker overhead

### SPA Catch-All Routing (FR-003)

When `gui_static_path` is provided (either via parameter or settings):

- Registers `GET /gui` route that serves `index.html` at the bare path
- Registers `GET /gui/{path:path}` catch-all route that:
  - Returns the requested static file if it exists on disk
  - Falls back to `index.html` for any 404 to support client-side SPA routing
  - Allows the frontend to handle route navigation without server-side routing configuration

The catch-all pattern enables single-page application (SPA) routing where all non-file paths are served with index.html, and the frontend JavaScript router handles navigation.

### ObservableFFmpegExecutor and AuditLogger (FR-004)

Both are DI-managed components created during lifespan startup in production mode:

- **ObservableFFmpegExecutor**: Wraps `RealFFmpegExecutor()` to provide observable/tracing capabilities over actual FFmpeg execution (created line 106)
- **AuditLogger**: Takes a sync SQLite connection with WAL journal mode enabled; tracks database mutations for audit trails (created lines 98-101)

Both can be overridden via `create_app()` parameters for testing, allowing injection of mocks or test implementations.

### Middleware Stack

Middleware is added in order (outermost first):
1. MetricsMiddleware: Collects Prometheus metrics for request count/duration
2. CorrelationIdMiddleware: Adds X-Correlation-ID header for request tracing

### Router Inclusion

All routers included on the FastAPI instance (lines 202-212):
- `health`: Liveness and readiness probes
- `videos`: Video listing, search, thumbnail, scan
- `projects`: Project CRUD and clip management
- `jobs`: Job status polling and cancellation
- `effects`: Effect listing, preview, application, and updates
- `compose`: Layout preset listing and application
- `audio`: Audio mix configuration and preview
- `filesystem`: Directory browsing
- `timeline`: Track and clip timeline management
- `batch`: Batch render job submission and progress
- `versions`: Version listing and restoration

### WebSocket

- `GET /ws`: Endpoint mounted via `add_websocket_route()` (line 213)
- Uses `ConnectionManager` from `app.state.ws_manager` for connection lifecycle and broadcasting

### Metrics Endpoint

- `GET /metrics`: Prometheus metrics endpoint mounted at `/metrics` using `prometheus_client.make_asgi_app()`

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.middleware.correlation.CorrelationIdMiddleware`: Request tracing middleware
- `stoat_ferret.api.middleware.metrics.MetricsMiddleware`: Prometheus metrics collection
- `stoat_ferret.api.routers.*`: All 11 router modules (audio, batch, compose, effects, filesystem, health, jobs, projects, timeline, versions, videos, ws)
- `stoat_ferret.api.services.scan.SCAN_JOB_TYPE, make_scan_handler`: Scan job handler factory
- `stoat_ferret.api.services.thumbnail.ThumbnailService`: Thumbnail generation service
- `stoat_ferret.api.settings.get_settings`: Configuration retrieval
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket connection management
- `stoat_ferret.db.async_repository.AsyncSQLiteVideoRepository, AsyncVideoRepository`: Video persistence
- `stoat_ferret.db.audit.AuditLogger`: Audit logging for mutations
- `stoat_ferret.db.clip_repository.AsyncClipRepository`: Clip persistence
- `stoat_ferret.db.project_repository.AsyncProjectRepository`: Project persistence
- `stoat_ferret.db.schema.create_tables_async`: Database schema initialization
- `stoat_ferret.db.timeline_repository.AsyncTimelineRepository`: Timeline persistence
- `stoat_ferret.db.version_repository.AsyncVersionRepository`: Version persistence
- `stoat_ferret.effects.registry.EffectRegistry`: Effect registry
- `stoat_ferret.ffmpeg.executor.FFmpegExecutor, RealFFmpegExecutor`: FFmpeg execution interface and implementation
- `stoat_ferret.ffmpeg.observable.ObservableFFmpegExecutor`: Observable FFmpeg executor wrapper
- `stoat_ferret.jobs.queue.AsyncioJobQueue`: Async job queue for background processing
- `stoat_ferret.logging.configure_logging`: Structured logging configuration

### External Dependencies

- `fastapi.FastAPI`: Web framework
- `fastapi.responses.FileResponse`: HTTP file response
- `aiosqlite`: Async SQLite client
- `prometheus_client.make_asgi_app`: Prometheus metrics ASGI application
- `structlog`: Structured logging

## Relationships

- **Used by:** Entry point (`__main__.py` calls `create_app()` and starts uvicorn)
- **Uses:** All routers, middleware, database repositories, FFmpeg executor, job queue, WebSocket manager, audit logger
