# Codebase Patterns — v009 Research

## 1. Constructor DI Pattern (create_app)

**File:** `src/stoat_ferret/api/app.py:99-179`

```python
def create_app(
    *,
    video_repository: AsyncVideoRepository | None = None,
    project_repository: AsyncProjectRepository | None = None,
    clip_repository: AsyncClipRepository | None = None,
    job_queue: AsyncioJobQueue | None = None,
    ws_manager: ConnectionManager | None = None,
    effect_registry: EffectRegistry | None = None,
    gui_static_path: str | Path | None = None,
) -> FastAPI:
```

Dependencies stored on `app.state` (lines 142-152). When any repo is injected, `app.state._deps_injected = True` skips lifespan DB setup. Router dependency functions check `app.state` first, falling back to lifespan-created instances.

**Pattern for v009:** Add `ffmpeg_executor` and `audit_logger` kwargs following this same pattern.

## 2. Idempotent Handler Registration

**File:** `src/stoat_ferret/logging.py:52-58`

```python
has_stream_handler = any(type(h) is logging.StreamHandler for h in root.handlers)
if not has_stream_handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)
```

Uses exact type match (`type(h) is`) to avoid matching subclasses. Tested in `tests/test_logging_startup.py:39-51`.

**Pattern for v009:** BL-057 must add `type(h) is RotatingFileHandler` guard.

## 3. Conditional Static Mount

**File:** `src/stoat_ferret/api/app.py:169-177`

```python
effective_gui_path = gui_static_path
if effective_gui_path is None and not has_injected:
    effective_gui_path = settings.gui_static_path
if effective_gui_path is not None:
    gui_dir = Path(effective_gui_path)
    if gui_dir.is_dir():
        app.mount("/gui", StaticFiles(directory=gui_dir, html=True), name="gui")
```

Mount only activates when directory exists. Default path: `"gui/dist"` from settings.

**Pattern for v009:** BL-063 SPA fallback route must also be conditional on `gui_dir.is_dir()`.

## 4. Repository count() Pattern

**File:** `src/stoat_ferret/db/async_repository.py`

Protocol (line 100):
```python
async def count(self) -> int: ...
```

SQLite impl (lines 210-215):
```python
async def count(self) -> int:
    cursor = await self._conn.execute("SELECT COUNT(*) FROM videos")
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])
```

InMemory impl (lines 365-367):
```python
async def count(self) -> int:
    return len(self._videos)
```

**Usage in videos router** (`routers/videos.py:72-73`):
```python
videos = await repo.list_videos(limit=limit, offset=offset)
total = await repo.count()
```

**Gap:** `AsyncProjectRepository` (in `db/project_repository.py:18-86`) has NO `count()` method. Projects router uses `total=len(projects)` (line 113).

## 5. WebSocket Event System

**Events:** `src/stoat_ferret/api/websocket/events.py:12-19`
- `HEALTH_STATUS`, `SCAN_STARTED`, `SCAN_COMPLETED`, `PROJECT_CREATED`, `HEARTBEAT`

**Builder:** `build_event(event_type, payload, correlation_id)` returns dict with type, payload, timestamp.

**Manager:** `src/stoat_ferret/api/websocket/manager.py` — `broadcast(message: dict)` sends to all connected clients.

**Access:** `request.app.state.ws_manager` (stored at `app.py:149`).

**Gap:** No router calls `broadcast()`. Only the heartbeat loop in `ws.py:29-51` sends messages.

## 6. Observable FFmpeg Executor

**File:** `src/stoat_ferret/ffmpeg/observable.py:23-100`

Constructor: `__init__(self, wrapped: FFmpegExecutor)` — decorator pattern wrapping any executor.

Metrics (`ffmpeg/metrics.py:11-26`):
- `ffmpeg_executions_total` (Counter: success/failure)
- `ffmpeg_execution_duration_seconds` (Histogram: 0.1s-300s buckets)
- `ffmpeg_active_processes` (Gauge)

Currently unused. Base executor wired directly at `app.py:79-82`:
```python
thumbnail_service = ThumbnailService(
    executor=RealFFmpegExecutor(),
    thumbnail_dir=settings.thumbnail_dir,
)
```

## 7. AuditLogger

**File:** `src/stoat_ferret/db/audit.py:12-107`

Constructor: `__init__(self, conn: sqlite3.Connection)` — requires synchronous SQLite connection.

Repositories accepting it:
- `SQLiteVideoRepository` (`db/repository.py:125`): `audit_logger: AuditLogger | None = None`
- `AsyncSQLiteVideoRepository` (`db/async_repository.py:136`): `audit_logger: AuditLogger | None = None`

Currently always `None`. The async repo only uses audit in `add()` (line 169-170), not in update/delete.

## 8. Router Dependency Pattern

**File:** `src/stoat_ferret/api/routers/videos.py:34-49`

```python
async def get_repository(request: Request) -> AsyncVideoRepository:
    repo = getattr(request.app.state, "video_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteVideoRepository(request.app.state.db)
```

Check `app.state` first (injected), fall back to creating from lifespan resources.
