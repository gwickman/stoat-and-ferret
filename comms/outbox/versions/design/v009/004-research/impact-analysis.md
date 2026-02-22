# Impact Analysis — v009

## Dependencies (code/tools/configs affected)

### Theme 1: observability-pipeline

| Item | Files Modified | Dependencies |
|------|---------------|-------------|
| BL-059 | `api/app.py` (lifespan + create_app), test conftest | `ffmpeg/observable.py`, `ffmpeg/metrics.py` (existing, unchanged) |
| BL-060 | `api/app.py` (lifespan + create_app), test conftest | `db/audit.py` (existing, unchanged), async repos |
| BL-057 | `logging.py`, `api/app.py` (lifespan call), `.gitignore` | stdlib `logging.handlers.RotatingFileHandler` only |

### Theme 2: gui-runtime-fixes

| Item | Files Modified | Dependencies |
|------|---------------|-------------|
| BL-063 | `api/app.py` (SPA route) | `gui/dist/index.html` (must exist for route to activate) |
| BL-064 | `db/project_repository.py` (protocol + 2 impls), `api/routers/projects.py` | Mirrors existing `AsyncVideoRepository.count()` pattern |
| BL-065 | `api/routers/projects.py`, `api/routers/videos.py` (scan endpoint) | `websocket/manager.py`, `websocket/events.py` (existing) |

## Breaking Changes

**None identified.** All changes are additive:
- BL-059/060: Add new DI wiring — existing code unaffected
- BL-057: Adds file handler alongside existing stdout — no behavior change
- BL-063: Adds fallback route — existing static serving unchanged
- BL-064: Adds count() method — API response `total` field becomes accurate
- BL-065: Adds broadcast calls — frontend already handles events

**Note on BL-064:** The `total` field value will change from page-size to true count. Any frontend code relying on the incorrect behavior would break, but the frontend pagination already expects the correct total.

## Test Infrastructure Needs

### New Tests Required

| Item | Test Type | Description |
|------|-----------|-------------|
| BL-059 | Unit | Verify ObservableFFmpegExecutor is the active executor; verify metrics populated after operation |
| BL-059 | Integration | Verify structlog output contains FFmpeg duration and correlation_id |
| BL-060 | Unit | Verify AuditLogger receives mutations from repositories |
| BL-060 | Integration | Verify audit entries created after CRUD operations |
| BL-057 | Unit | Verify RotatingFileHandler added; verify idempotency guard |
| BL-057 | Unit | Verify logs/ directory created on startup |
| BL-063 | Integration | Verify /gui/library returns 200 with index.html content |
| BL-063 | Integration | Verify /gui/nonexistent returns SPA content, not 404 |
| BL-064 | Unit | Verify AsyncProjectRepository.count() returns correct total |
| BL-064 | Integration | Verify GET /api/v1/projects returns correct total field |
| BL-065 | Integration | Verify WebSocket receives SCAN_STARTED/COMPLETED after scan |
| BL-065 | Integration | Verify WebSocket receives PROJECT_CREATED after project creation |

### Existing Tests Affected

- `tests/test_api/conftest.py`: May need updates if `create_app()` signature changes (BL-059/060)
- `tests/test_logging_startup.py`: Add tests for file handler (BL-057)
- `tests/test_api/test_di_wiring.py`: Verify new DI params stored on app.state

### E2E Test Impact

- BL-063: After SPA fallback works, E2E tests can navigate directly to sub-paths (LRN-023). New E2E tests must use explicit timeouts (LRN-043).
- BL-065: E2E tests for ActivityLog can verify real events appear (not just heartbeats).

## Documentation Updates Required

| Doc | Update | Reason |
|-----|--------|--------|
| `docs/design/05-api-specification.md` | Add SPA fallback route documentation | BL-063 |
| `AGENTS.md` | No changes needed | All patterns already documented |
| `.gitignore` | Add `logs/` entry | BL-057 AC4 |
