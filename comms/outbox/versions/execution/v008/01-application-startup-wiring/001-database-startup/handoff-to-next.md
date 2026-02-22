# Handoff: 001-database-startup

## What was done

- `create_tables_async()` is now available in `src/stoat_ferret/db/schema.py` and exported from the `db` package.
- The FastAPI lifespan calls `create_tables_async(db)` immediately after opening the aiosqlite connection and before creating repositories.
- All DDL uses `IF NOT EXISTS`, so it's safe to call on every startup.
- The `_deps_injected` guard skips the entire DB setup path (including schema creation) in test mode.

## What the next feature should know

- The schema creation call is in `app.py:lifespan()`, after `app.state.db = await aiosqlite.connect(...)` and before `AsyncSQLiteVideoRepository(app.state.db)`.
- If new tables are added in later features, update both `create_tables()` (sync) and `create_tables_async()` (async) in `schema.py`.
- `get_settings()` uses `@lru_cache` — tests that modify env vars and call the lifespan must call `get_settings.cache_clear()` before and after.
