# Test Strategy: v008

## Theme 1: 01-application-startup-wiring

### Feature 001: database-startup (BL-058)

**Unit tests:**
- Test create_tables_async() creates all 12 expected DDL objects (tables, indexes, FTS, triggers) on a fresh in-memory database
- Test create_tables_async() is idempotent (calling twice does not error)

**System/Golden scenarios:**
- Test application lifespan creates schema on fresh database (integration test with real lifespan startup)
- Test _deps_injected=True bypass skips schema creation (test mode behavior preserved)

**Parity tests:**
- Not applicable (no API/MCP tool changes)

**Contract tests:**
- Not applicable (no new DTO models)

**Replay fixtures:**
- Not applicable (no new execution patterns)

**Existing test modifications:**
- Replace local create_tables_async() in test_async_repository_contract.py with import from schema.py
- Replace local create_tables_async() in test_project_repository_contract.py with import from schema.py
- Replace local create_tables_async() in test_clip_repository_contract.py with import from schema.py
- Verify all 3 test files pass with shared function (DDL coverage must match the most complete copy: 12 statements)

---

### Feature 002: logging-startup (BL-056)

**Unit tests:**
- Test configure_logging() is called during lifespan startup (mock/spy verification)
- Test settings.log_level string is correctly converted to logging int (getattr(logging, level))
- Test uvicorn log_level reads from settings.log_level.lower() instead of hardcoded "info"

**System/Golden scenarios:**
- Test STOAT_LOG_LEVEL=DEBUG produces visible debug output (capture stdout/stderr)
- Test STOAT_LOG_LEVEL=INFO produces structured log output from at least one structlog logger
- Test default log level (INFO) works without explicit env var

**Parity tests:**
- Not applicable (no API/MCP tool changes)

**Contract tests:**
- Not applicable (no new DTO models)

**Replay fixtures:**
- Not applicable (no new execution patterns)

**Existing test modifications:**
- Verify no existing tests break from newly-active logging (logging was previously silent; activation may add unexpected stdout)
- If tests capture stdout, ensure log output doesn't cause false failures

---

### Feature 003: orphaned-settings (BL-062)

**Unit tests:**
- Test FastAPI app created with debug=True when settings.debug=True
- Test FastAPI app created with debug=False when settings.debug=False (default)
- Test ws.py reads ws_heartbeat_interval from settings instead of constant
- Test that DEFAULT_HEARTBEAT_INTERVAL constant is removed or no longer referenced

**System/Golden scenarios:**
- Test STOAT_DEBUG=true enables FastAPI debug mode (verify app.debug attribute)
- Test STOAT_WS_HEARTBEAT_INTERVAL=15 changes heartbeat loop interval

**Parity tests:**
- Not applicable (no API/MCP tool changes)

**Contract tests:**
- Not applicable (no new DTO models)

**Replay fixtures:**
- Not applicable (no new execution patterns)

**Existing test modifications:**
- None expected (settings wiring is additive; defaults match existing behavior)

---

## Theme 2: 02-ci-stability

### Feature 001: flaky-e2e-fix (BL-055)

**Unit tests:**
- Not applicable (E2E test modification only)

**System/Golden scenarios:**
- Not applicable (test infrastructure change, not application behavior)

**Parity tests:**
- Not applicable (no API/MCP tool changes)

**Contract tests:**
- Not applicable (no new DTO models)

**Replay fixtures:**
- Not applicable (no new execution patterns)

**E2E validation:**
- Verify toBeHidden() assertion passes with explicit { timeout: 10_000 }
- AC requires 10 consecutive CI runs passing — this is a post-merge validation that cannot be automated in a single PR
- Verify no other E2E tests require retry loops
- Verify tested functionality unchanged (modal still opens and closes correctly)

---

## Test Coverage Summary

| Theme | Feature | New Unit Tests | System Tests | E2E Changes | Existing Test Mods |
|-------|---------|---------------|-------------|-------------|-------------------|
| 01 | 001-database-startup | 2 | 2 | None | 3 (replace helpers) |
| 01 | 002-logging-startup | 3 | 3 | None | Verify no breakage |
| 01 | 003-orphaned-settings | 4 | 2 | None | None |
| 02 | 001-flaky-e2e-fix | 0 | 0 | 1 (timeout) | None |

**Total new tests:** ~16 (9 unit + 7 system/integration)
**Existing test modifications:** 3 files (test helper replacement)
**E2E modifications:** 1 file (timeout parameter)
