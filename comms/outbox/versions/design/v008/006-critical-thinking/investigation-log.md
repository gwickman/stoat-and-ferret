# Investigation Log: v008 Critical Thinking

## Investigation 1: Logging activation impact on tests

**Goal:** Determine if calling configure_logging() at startup breaks existing tests.

**Queries performed:**
1. Searched tests/ for capsys, capfd fixture usage
2. Searched tests/ for assertions on stdout/stderr content
3. Read src/stoat_ferret/logging.py:15-56 (configure_logging implementation)
4. Read tests/test_logging.py (4 tests calling configure_logging)
5. Read tests/test_observable.py:250 (capsys usage)
6. Read src/stoat_ferret/api/app.py:38-60 (_deps_injected bypass scope)
7. Searched for tests creating apps without dependency injection

**Findings:**
- `configure_logging()` at logging.py:50-54 calls `root.addHandler(handler)` without checking for existing handlers — NOT idempotent
- `test_logging.py` calls `structlog.reset_defaults()` but never removes stdlib logging handlers — handler accumulation across 4 tests
- `test_observable.py:250` accepts capsys but doesn't assert on captured output — low risk
- Tests asserting on `ExecutionResult.stdout` (test_executor.py) check data fields, not system stdout — no risk
- `_deps_injected=True` bypass at app.py:38-60 only skips DB/queue init, not full lifespan
- Tests without injection (test_app.py:12-32, test_di_wiring.py:78-82, test_worker.py:66) exercise full lifespan

**Conclusion:** Real risk. Mitigated by making configure_logging() idempotent.

---

## Investigation 2: configure_logging() placement relative to _deps_injected guard

**Goal:** Determine correct placement for logging initialization in the lifespan.

**Queries performed:**
1. Read src/stoat_ferret/api/app.py lifespan function structure
2. Analyzed what _deps_injected guard skips vs. allows

**Findings:**
- The guard at app.py:38-60 is a conditional that skips database connection, repository creation, and job queue startup
- Code before the guard executes in ALL contexts (production and test mode)
- Code after the guard (inside it) only executes in production mode
- BL-056 AC #1 requires logging "before any request handling" — placing before guard satisfies this
- Logging should be available in test mode for debugging

**Conclusion:** Place before guard. Combined with idempotency fix from Investigation 1, this is safe.

---

## Investigation 3: uvicorn log_level format compatibility

**Goal:** Verify settings.log_level values are compatible with uvicorn.run() log_level parameter.

**Queries performed:**
1. Read src/stoat_ferret/api/settings.py:53 (log_level field definition)
2. Read src/stoat_ferret/api/__main__.py:23-28 (uvicorn.run call)
3. Read tests/test_api/test_settings.py:69-73 (log level test)

**Findings:**
- Settings: `Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` (uppercase)
- Uvicorn current: hardcoded `log_level="info"` (lowercase)
- Uvicorn expects lowercase strings: "debug", "info", "warning", "error", "critical"
- Uvicorn uses "warning" (not "warn") — consistent with Python logging standard
- `.lower()` conversion handles all 5 Literal values correctly

**Conclusion:** Risk resolved. `.lower()` conversion is correct and complete.

---

## Investigation 4: WebSocket heartbeat settings access safety

**Goal:** Verify replacing DEFAULT_HEARTBEAT_INTERVAL with get_settings().ws_heartbeat_interval is safe.

**Queries performed:**
1. Read src/stoat_ferret/api/routers/ws.py:15-42 (heartbeat usage)
2. Read src/stoat_ferret/api/settings.py:93-100 (get_settings implementation)
3. Searched for get_settings() usage across codebase (4 callsites found)
4. Read settings.py:70-75 (ws_heartbeat_interval field definition)

**Findings:**
- `DEFAULT_HEARTBEAT_INTERVAL = 30` used at ws.py:42 inside `websocket_endpoint()` handler — connection time, not import time
- `get_settings()` decorated with `@lru_cache` — returns cached instance, safe for concurrent access
- Settings default `ws_heartbeat_interval = 30` matches constant value
- Field has `ge=1` validation — minimum 1 second enforced
- get_settings() already used in 4 other files: __main__.py, app.py (2 callsites), videos.py
- ws.py does not currently import from settings — new import needed

**Conclusion:** Risk resolved. Replacement is safe. Pattern is established.

---

## Dead ends

None. All 4 investigations produced actionable findings.
