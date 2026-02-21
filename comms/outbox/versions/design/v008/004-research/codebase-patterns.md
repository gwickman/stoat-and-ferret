# Codebase Patterns — v008 Research

## Lifespan Startup Pattern

The FastAPI lifespan context manager at `src/stoat_ferret/api/app.py:38-89` is the canonical location for startup tasks.

**Current startup sequence:**
1. Create `ConnectionManager` if not injected (line 54-55)
2. Skip all DB/worker setup if `app.state._deps_injected = True` (line 58-60)
3. Open async SQLite connection via `aiosqlite.connect()` (line 65-66)
4. Set row factory (line 66)
5. Create repositories, services, job queue (lines 69-76)
6. Start job worker task (line 77)

**Test mode bypass:** `app.state._deps_injected = True` causes early return at line 58-60, skipping all startup. BL-056 and BL-058 wiring must respect this bypass.

## Settings Pattern

`src/stoat_ferret/api/settings.py` — `Settings` class (Pydantic BaseSettings):

| Field | Type | Default | Consumed? |
|-------|------|---------|-----------|
| `database_path` | `str` | `"data/stoat.db"` | Yes — `app.py:65` |
| `api_host` | `str` | `"127.0.0.1"` | Yes — `__main__.py:25` |
| `api_port` | `int` | `8000` | Yes — `__main__.py:26` |
| `debug` | `bool` | `False` | **NO** |
| `log_level` | `Literal[...]` | `"INFO"` | **NO** |
| `thumbnail_dir` | `str` | `"data/thumbnails"` | Yes — `app.py:73` |
| `gui_static_path` | `str` | `"gui/dist"` | Yes — `app.py:163` |
| `ws_heartbeat_interval` | `int` | `30` | **NO** |
| `allowed_scan_roots` | `list[str]` | `[]` | Yes — `videos.py:195` |

Settings accessed via `get_settings()` function (cached) or direct `Settings()` instantiation.

## Logging Infrastructure

**`src/stoat_ferret/logging.py:15`** — `configure_logging(json_format: bool = True, level: int = logging.INFO) -> None`

- Configures structlog with JSON or console renderer
- Sets stdlib logging level via `logging.basicConfig(level=level)`
- Adds structlog processors for timestamps, log level, caller info
- **Never called** — no invocation found anywhere in codebase

**9 modules with `structlog.get_logger(__name__)`:**
1. `src/stoat_ferret/api/app.py`
2. `src/stoat_ferret/api/routers/effects.py`
3. `src/stoat_ferret/api/routers/ws.py`
4. `src/stoat_ferret/api/services/scan.py`
5. `src/stoat_ferret/api/services/thumbnail.py`
6. `src/stoat_ferret/api/websocket/manager.py`
7. `src/stoat_ferret/effects/registry.py`
8. `src/stoat_ferret/ffmpeg/observable.py`
9. `src/stoat_ferret/jobs/queue.py`

## Database Schema Creation

**Sync function:** `src/stoat_ferret/db/schema.py:120` — `create_tables(conn: sqlite3.Connection) -> None`
- Executes 12 DDL statements (tables, indexes, FTS, triggers)
- Commits transaction
- Exported from `src/stoat_ferret/db/__init__.py`

**Async test duplicates** (3 copies with inconsistent DDL coverage):

| File | DDL Count | Missing |
|------|-----------|---------|
| `tests/test_async_repository_contract.py:37-47` | 8 | projects, clips tables + indexes |
| `tests/test_project_repository_contract.py:52-63` | 10 | clips table + indexes |
| `tests/test_clip_repository_contract.py:56-70` | 12 | None (complete) |

**Alembic:** Configured at `alembic.ini`, 5 sequential migrations in `alembic/versions/`. CI verifies migration reversibility. E2E tests use `alembic upgrade head` for schema setup.

## WebSocket Heartbeat

`src/stoat_ferret/api/routers/ws.py:15` — `DEFAULT_HEARTBEAT_INTERVAL = 30`

Used at line 42: `heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket, DEFAULT_HEARTBEAT_INTERVAL))`

The `websocket_endpoint()` function does not access settings. Wiring requires calling `get_settings()` inside the endpoint.

## FastAPI Instantiation

`src/stoat_ferret/api/app.py:119-124`:
```python
app = FastAPI(
    title="stoat-and-ferret",
    description="AI-driven video editor API",
    version="0.3.0",
    lifespan=lifespan,
)
```
No `debug=` kwarg. BL-062 adds `debug=settings.debug`.

## uvicorn Configuration

`src/stoat_ferret/api/__main__.py:23-28`:
```python
uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_level="info")
```
`log_level` is hardcoded `"info"`. BL-056 changes to `settings.log_level.lower()`.

## E2E Test Patterns

`gui/e2e/project-creation.spec.ts:37` — `toBeHidden()` with no explicit timeout (default 5s).

Other E2E timeout patterns:
- `scan.spec.ts`: `timeout: 10000`
- `accessibility.spec.ts`: `timeout: 15_000`
- `effect-workshop.spec.ts`: mixed 5-15s
- `navigation.spec.ts`: default (no explicit)

Playwright config at `gui/playwright.config.ts` — no custom timeout settings configured.
