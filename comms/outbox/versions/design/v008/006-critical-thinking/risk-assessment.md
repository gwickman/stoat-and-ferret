# Risk Assessment: v008

## Risk: Logging activation breaks existing tests

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Searched all tests for capsys/capfd fixtures, stdout assertions, and configure_logging() calls. Analyzed _deps_injected bypass scope. Read configure_logging() implementation.
- **Finding**: `configure_logging()` unconditionally adds a `StreamHandler(sys.stdout)` to the root logger via `root.addHandler(handler)` without checking for existing handlers. Multiple calls accumulate duplicate handlers. `test_logging.py` calls `configure_logging()` 4 times but only resets structlog — never removes root logger handlers. One test (`test_observable.py`) uses capsys but doesn't assert on captured content. Tests checking `ExecutionResult.stdout` fields (not system stdout) are safe.
- **Resolution**: Make `configure_logging()` idempotent: check if a handler is already attached before adding. Add root logger handler cleanup to `test_logging.py`. This is a **new implementation requirement** for Feature 002-logging-startup.
- **Affected themes/features**: Theme 1, Feature 002 (logging-startup)

## Risk: E2E "10 consecutive CI runs" validation is not automatable in a single PR

- **Original severity**: medium
- **Category**: Accept with mitigation
- **Investigation**: Reviewed the AC requirement and PR workflow. The fix (adding explicit 10s timeout matching existing project patterns in scan.spec.ts and accessibility.spec.ts) addresses the identified root cause (default 5s Playwright assertion timeout too short for GitHub Actions).
- **Finding**: A single PR cannot prove 10 consecutive passing runs before merge. This is inherently a post-merge validation. The root cause analysis is sound and the fix follows established project patterns.
- **Resolution**: Accept the fix based on root cause analysis. Validate reliability post-merge by monitoring the next 10 CI runs. If the flake reappears, create a follow-up backlog item. The AC should be interpreted as "passes reliably in CI" with 10 runs as the validation criterion, not a blocking pre-merge gate.
- **Affected themes/features**: Theme 2, Feature 001 (flaky-e2e-fix)

## Risk: create_tables_async() may need schema evolution strategy

- **Original severity**: low
- **Category**: Accept with mitigation
- **Investigation**: No investigation needed for v008 per Task 005. CREATE TABLE IF NOT EXISTS is idempotent for initial creation and v008 introduces no schema changes.
- **Finding**: Risk is real for future versions but not for v008. The IF NOT EXISTS pattern is safe and sufficient for the current scope.
- **Resolution**: Document Alembic as the upgrade path (per LRN-029). Trigger: when v009+ requires the first schema migration. No design change needed for v008.
- **Affected themes/features**: Theme 1, Feature 001 (database-startup) — documentation only

## Risk: Shared modification point (app.py) creates merge conflict potential

- **Original severity**: low
- **Category**: Accept with mitigation
- **Investigation**: No investigation needed — already mitigated by strict sequential execution order.
- **Finding**: Sequential feature execution (001 → 002 → 003) within Theme 1 eliminates merge conflicts on the shared app.py file.
- **Resolution**: Mitigated by design. The execution order is mandated by functional dependencies (database → logging → settings). No design change needed.
- **Affected themes/features**: Theme 1, all features

## Risk: configure_logging() placement relative to _deps_injected guard

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Analyzed the _deps_injected bypass in app.py. The guard at app.py:38-60 skips DB and worker setup but does NOT skip the full lifespan. If configure_logging() is placed before the guard, it executes in all contexts including tests. If placed after, test mode has no logging.
- **Finding**: Placing configure_logging() BEFORE the guard is correct for observability (logging should work in all modes). However, this requires configure_logging() to be idempotent (see Risk #1) to prevent handler accumulation across test runs. The `_deps_injected` bypass only controls DB/queue init, not logging — this is the right separation of concerns.
- **Resolution**: Place configure_logging() before the _deps_injected guard. Make it idempotent. This aligns with BL-056 AC #1 ("before any request handling") and ensures logging is available in test mode for debugging.
- **Affected themes/features**: Theme 1, Feature 002 (logging-startup)

## Risk: uvicorn log_level format mismatch

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Read settings.py (Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]) and __main__.py (hardcoded "info"). Verified uvicorn expects lowercase log level strings.
- **Finding**: Uvicorn accepts "debug", "info", "warning", "error", "critical" — all lowercase. Settings defines uppercase Literal values. The `.lower()` conversion handles all cases correctly. Crucially, uvicorn uses "warning" (not "warn"), which matches the Python logging standard.
- **Resolution**: Risk resolved. The conversion `settings.log_level.lower()` is correct and complete. No design change needed.
- **Affected themes/features**: Theme 1, Feature 002 (logging-startup)

## Risk: WebSocket heartbeat settings access pattern

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Read ws.py to check DEFAULT_HEARTBEAT_INTERVAL usage timing. Verified get_settings() implementation (@lru_cache decorator). Checked existing get_settings() usage patterns across 4 other callsites.
- **Finding**: The heartbeat interval is read at **connection time** (inside `websocket_endpoint()` handler), not at module import time. `get_settings()` is @lru_cache-decorated, returning the same cached Settings instance on every call. The default value (30) matches the current hardcoded constant. The pattern of calling get_settings() at runtime is already established across 4 other files in the codebase.
- **Resolution**: Risk resolved. Replacing `DEFAULT_HEARTBEAT_INTERVAL` with `get_settings().ws_heartbeat_interval` is safe. No design change needed.
- **Affected themes/features**: Theme 1, Feature 003 (orphaned-settings)
