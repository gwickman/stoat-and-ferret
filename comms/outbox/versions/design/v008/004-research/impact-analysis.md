# Impact Analysis — v008 Research

## Dependencies (Code/Tools/Configs Affected)

### BL-055: Flaky E2E Test
- **Files modified**: `gui/e2e/project-creation.spec.ts` (line 37 — add explicit timeout)
- **No other files affected**: The fix is isolated to the test assertion
- **CI dependency**: Validation requires 10 consecutive CI runs (AC #1)

### BL-056: Wire Structured Logging
- **Files modified**:
  - `src/stoat_ferret/api/app.py` — add `configure_logging()` call in lifespan
  - `src/stoat_ferret/api/__main__.py` — change `log_level="info"` to `settings.log_level.lower()`
- **Type conversion required**: `getattr(logging, settings.log_level)` in lifespan
- **Import added**: `from stoat_ferret.logging import configure_logging` in app.py
- **Test bypass**: Must be inside `_deps_injected` guard or before it

### BL-058: Wire Database Startup
- **Files modified**:
  - `src/stoat_ferret/api/app.py` — add schema creation call in lifespan
  - `src/stoat_ferret/db/schema.py` — add `create_tables_async()` function
  - `tests/test_async_repository_contract.py` — replace local helper with import
  - `tests/test_project_repository_contract.py` — replace local helper with import
  - `tests/test_clip_repository_contract.py` — replace local helper with import
- **Alembic**: No changes required; remains available as upgrade path
- **Test bypass**: Schema creation must be inside `_deps_injected` guard

### BL-062: Wire Orphaned Settings
- **Files modified**:
  - `src/stoat_ferret/api/app.py` — add `debug=settings.debug` to FastAPI constructor
  - `src/stoat_ferret/api/routers/ws.py` — replace `DEFAULT_HEARTBEAT_INTERVAL` with `get_settings().ws_heartbeat_interval`
  - `src/stoat_ferret/api/__main__.py` — potentially add `debug` kwarg (if not handled by FastAPI)
- **Settings access**: `ws.py` needs `get_settings()` import

## Breaking Changes

**None identified.** All v008 changes are additive wiring that connects existing infrastructure:
- BL-055: Test-only change, no functional impact
- BL-056: Activates previously-silent logging output (stdout change, not API change)
- BL-058: Auto-creates schema that was previously manual (additive)
- BL-062: Connects settings to consumers (enables configuration that was defined but inert)

## Test Infrastructure Needs

### New Tests Required
- **None** — all backlog items have ACs that are verifiable through existing test infrastructure

### Existing Test Modifications
- **BL-058**: Replace 3 local `create_tables_async()` helpers with imports from shared module
- **BL-056**: Verify no tests break from newly-active logging output (quick check — structlog defaults to stderr, tests typically don't capture stderr)

### CI Validation
- **BL-055**: Requires 10 consecutive green E2E runs (AC #1). This cannot be automated in a single PR — recommend verifying via CI history after merge.

## Documentation Updates Required

All are small, co-located sub-tasks (as identified in Task 003):
1. `docs/setup/02_development-setup.md` Section 5 — note automatic schema creation (BL-058)
2. `docs/setup/04_configuration.md` — update STOAT_DEBUG and STOAT_LOG_LEVEL descriptions (BL-056, BL-062)
3. C4 docs — update lifespan descriptions and Mermaid diagrams (BL-056, BL-058)

## Shared Modification Points

**`src/stoat_ferret/api/app.py`** is modified by BL-056, BL-058, and BL-062:
- BL-058: Add schema creation to lifespan
- BL-056: Add `configure_logging()` to lifespan
- BL-062: Add `debug=settings.debug` to FastAPI constructor

**`src/stoat_ferret/api/__main__.py`** is modified by BL-056 and BL-062:
- BL-056: Change `log_level` from hardcoded to `settings.log_level.lower()`
- BL-062: Potentially add `debug` kwarg (if uvicorn also needs it)

**Recommendation**: Sequence BL-058 → BL-056 → BL-062 within the theme to avoid merge conflicts on shared files, per Task 003 recommendation.
