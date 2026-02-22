# 004 Research & Investigation — v009

Research covered all 6 backlog items across 2 themes. All referenced classes, protocols, and patterns were located in the codebase and verified. 13 learnings were verified — all VERIFIED, none stale. One critical external finding: `StaticFiles(html=True)` does NOT provide SPA fallback routing; BL-063 requires a catch-all route pattern. No unresolvable unknowns remain.

## Research Questions

### Theme 1: observability-pipeline
1. What constructor parameters does `ObservableFFmpegExecutor` need and where is the base executor wired?
2. What is `AuditLogger`'s constructor signature and which repositories accept it?
3. How does `configure_logging()` implement idempotent handler registration?
4. What settings exist for log rotation?

### Theme 2: gui-runtime-fixes
5. Does `StaticFiles(html=True)` provide full SPA fallback for sub-paths?
6. Does `AsyncProjectRepository` have a `count()` method?
7. Where should `ConnectionManager.broadcast()` be called and what event types exist?

## Findings Summary

| Question | Finding | Impact |
|----------|---------|--------|
| Q1 | `ObservableFFmpegExecutor(wrapped: FFmpegExecutor)` — wraps any executor. Base wired at `app.py:80` as `RealFFmpegExecutor()` | Straightforward: wrap existing instantiation |
| Q2 | `AuditLogger(conn: sqlite3.Connection)` — `SQLiteVideoRepository` and `AsyncSQLiteVideoRepository` accept it as optional param | Need DB connection from lifespan |
| Q3 | Exact-type check `type(h) is logging.StreamHandler` prevents duplicates | Same pattern needed for `RotatingFileHandler` |
| Q4 | No rotation settings exist; `log_level` is the only logging setting | May add `log_backup_count` setting |
| Q5 | **No** — returns 404 for non-existent sub-paths. Confirmed via DeepWiki/Starlette source | Catch-all route needed before StaticFiles mount |
| Q6 | **Missing** — Protocol and both implementations lack `count()` | Must add to protocol + SQLite + InMemory impls |
| Q7 | No `broadcast()` calls in any router. Events defined in `websocket/events.py`. `ws_manager` on `app.state` | Must inject manager into scan/project routers |

## Unresolved Questions

None. All questions resolved through codebase investigation and external research.

## Recommendations

1. **BL-063 SPA fallback**: Add a catch-all `Route("/{path:path}")` or FastAPI route for `/gui/{path:path}` that returns `index.html`. Must be registered AFTER API routers but BEFORE the `StaticFiles` mount.
2. **BL-059/060 DI wiring**: Follow the established `create_app()` kwargs pattern. Add optional params for `ffmpeg_executor` and `audit_logger`.
3. **BL-057 file logging**: Extend `configure_logging()` with a second idempotent guard using `type(h) is RotatingFileHandler`. Create `logs/` directory on startup.
4. **BL-064 count()**: Copy `AsyncVideoRepository.count()` pattern exactly — add to protocol and both implementations.
5. **BL-065 WebSocket broadcasts**: Inject `ws_manager` into route dependency functions via `request.app.state.ws_manager`. Call `broadcast(build_event(...))` at operation completion points.
