# Wiring Audit: v003 & v004

Two wiring gaps found, both in v003/02-api-foundation/002-externalized-settings. Both are settings fields that were implemented with full validation but are never consumed at runtime — the code hardcodes defaults instead of reading from settings. All other v003 and v004 features are properly wired.

The known logging gap (BL-056: `log_level` + `configure_logging()`) is excluded per instructions.

## Per-Theme Summary

### v003/01-process-improvements
**No gaps.** Async repository, migration CI verification, and CI path filters are all properly wired and functional.

### v003/02-api-foundation
**2 gaps found** (both in 002-externalized-settings):
1. `settings.debug` defined but never consumed — not passed to `FastAPI(debug=...)` or `uvicorn.run()` (minor)
2. `settings.ws_heartbeat_interval` defined but hardcoded — `ws.py` uses `DEFAULT_HEARTBEAT_INTERVAL = 30` instead of reading from settings (minor)

All other features (app setup, health endpoints, middleware stack) are fully wired: all routers registered, all middleware added, DI pattern functional.

### v003/03-library-api
**No gaps.** All four endpoints (list/detail, search, scan, delete) are registered, repositories are instantiated via DI, and settings like `allowed_scan_roots` and `thumbnail_dir` are properly consumed.

### v003/04-clip-model
**No gaps.** Project and clip data models, repositories, and API endpoints are all implemented, registered, and wired through DI. Handoff notes mention future features (PATCH endpoint, overlap detection, timeline model) — these are planned work, not wiring gaps.

### v004/01-test-foundation
**No gaps.** In-memory test doubles are used in test fixtures, DI is wired into `create_app()`, and the fixture factory is exported and consumed in tests.

### v004/02-blackbox-contract
**No gaps.** Blackbox test catalog (30 tests), FFmpeg contract tests (21 tests), and search unification with parity tests (7 tests) are all present and passing.

### v004/03-async-scan
**No gaps.** Job queue infrastructure has a worker started/stopped in lifespan, async scan endpoint returns 202 with job polling, and scan handler is registered at startup. Documentation updated.

### v004/04-security-performance
**No gaps.** `validate_scan_path()` is wired into the scan endpoint with `allowed_scan_roots` from settings. Benchmark suite is runnable via `python -m benchmarks`.

### v004/05-devex-coverage
**No gaps.** Hypothesis added to dev deps, property marker registered, Rust coverage CI job added, coverage exclusions audited, Docker testing files present.

## Verification Method

- Read all completion reports and handoff-to-next.md files for v003 and v004
- Grepped for every settings field to verify consumption outside settings.py
- Verified all routers registered in `app.py` (health, videos, projects, jobs, effects, websocket)
- Verified all middleware registered (MetricsMiddleware, CorrelationIdMiddleware)
- Verified lifespan hooks wire up database, job queue worker, thumbnail service, scan handler, and WebSocket manager
- Checked all public functions/classes for import and usage outside their own modules
