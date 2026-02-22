# Theme 01: application-startup-wiring — Retrospective

## Summary

Wired three pieces of existing but disconnected infrastructure into the FastAPI application lifespan startup sequence: database schema creation, structured logging configuration, and two orphaned settings fields (`debug`, `ws_heartbeat_interval`). After this theme, a fresh application start produces a fully functional system without manual intervention — tables are created, logging is configured from settings, and every `Settings` field is consumed by production code.

## Deliverables

| Feature | Status | Acceptance | Notes |
|---------|--------|------------|-------|
| 001-database-startup | Complete | 5/5 pass | `create_tables_async()` added to schema.py, called in lifespan; 3 duplicate test helpers consolidated |
| 002-logging-startup | Complete | 7/7 pass | `configure_logging()` wired into lifespan with `settings.log_level`; idempotent handler guard added; uvicorn log level made configurable |
| 003-orphaned-settings | Complete | 3/3 pass | `settings.debug` wired to `FastAPI(debug=...)`; `settings.ws_heartbeat_interval` replaces hardcoded constant in ws.py |

All 3 features passed all quality gates (ruff, mypy, pytest) on first iteration.

## Metrics

- **Test count progression:** 868 → 883 → 889 (21 new tests added)
- **Coverage:** 92.71% (exceeds 80% threshold)
- **Source files changed:** `app.py`, `schema.py`, `db/__init__.py`, `logging.py`, `__main__.py`, `ws.py`
- **Test files added:** `test_database_startup.py`, `test_logging_startup.py`, `test_orphaned_settings.py`
- **Net lines of code (source + tests):** ~540 added, ~80 removed (duplicate test helpers consolidated)

## Key Decisions

### Database schema creation placement
**Context:** Needed to decide where in the lifespan to call `create_tables_async()`.
**Choice:** Placed after DB connection but before repository creation.
**Outcome:** Clean ordering — DB must exist before repos can use it. Fresh databases are fully functional after a single app start.

### Logging configured before deps guard
**Context:** `configure_logging()` could be placed before or after the `_deps_injected` guard in lifespan.
**Choice:** Placed before the guard so both production and test modes get consistent logging.
**Outcome:** Log output works identically in tests and production.

### FastAPI debug vs uvicorn debug
**Context:** Implementation plan suggested wiring `settings.debug` to both `FastAPI()` and `uvicorn.run()`.
**Choice:** Only wired to `FastAPI(debug=...)` because `uvicorn.run()` doesn't accept a `debug` kwarg (mypy caught this).
**Outcome:** Correct behavior — FastAPI's debug mode controls error detail, which is the actual consumer.

## Learnings

### What Went Well
- All three features shared the same modification point (`app.py` lifespan), making the theme cohesive and reducing context-switching
- Consolidating 3 duplicate `create_tables_async` test helpers into a shared import improved maintainability
- mypy caught the invalid `uvicorn.run(debug=...)` kwarg before it reached production
- Quality gates passed on first iteration for all features — the theme was well-scoped

### What Could Improve
- The orphaned settings audit (feature 003) confirmed all 9 `Settings` fields are now consumed. This kind of "nothing is unused" assertion could be automated as a lint check

### Patterns Discovered
- **Idempotent startup wiring:** Both `create_tables_async` (IF NOT EXISTS) and `configure_logging` (handler dedup guard) were made idempotent. This is the right pattern for lifespan functions that may be called multiple times in tests
- **Settings → consumer traceability:** Checking that every settings field has a consumer is a useful completeness check after wiring work

## Technical Debt

- No quality-gaps.md files were generated — all features passed cleanly
- No new technical debt introduced by this theme
- The theme resolved existing debt: 3 duplicate test helpers were consolidated, and 2 settings fields that were previously defined but unused are now wired

## Action Items

- [ ] Consider adding a lint/test that verifies all `Settings` fields are consumed by production code (prevents future orphaned settings)
- [ ] The lifespan function in `app.py` is growing — monitor complexity as more startup tasks are added in future versions
