# Impact Summary — v009

## Small Impacts (sub-task scope)

### Documentation Updates (caused by BL-063 — SPA routing)
- **#1**: Remove "Known Limitation — SPA Fallback" from `docs/design/08-gui-architecture.md` (line 60)
- **#2**: Remove SPA fallback known limitation from `docs/design/05-api-specification.md` (lines 1501-1508)
- **#3**: Update GUI Static Files description in `docs/design/05-api-specification.md` (lines 1220-1230) to describe actual fallback mechanism

### Documentation Updates (caused by BL-064 — pagination fix)
- **#4**: Add pagination fields (`total`, `limit`, `offset`) to List Projects response example in `docs/design/05-api-specification.md` (lines 382-399)

### Configuration (caused by BL-057 — file logging)
- **#5**: Add `logs/` to `.gitignore` (already required by AC4)

### Caller Wiring (caused by BL-065 — WebSocket broadcasts)
- **#8**: Update `make_scan_handler` factory to accept and use `ws_manager` for SCAN_STARTED/SCAN_COMPLETED broadcasts

### Test Updates (caused by BL-064 — pagination fix)
- **#9**: Update pagination test assertions in `test_blackbox/test_edge_cases.py` to expect true database total count

### Caller Wiring (caused by BL-060 — AuditLogger)
- **#10**: Pass AuditLogger instance to `AsyncSQLiteVideoRepository` in `app.py` lifespan function

## Substantial Impacts (feature scope)

### BL-060 Scope Extension — AuditLogger for Project Repositories
- **#6**: `AsyncProjectRepository` protocol and both implementations (SQLite, InMemory) need an `audit_logger` parameter. Without this, BL-060 AC2 ("Database mutations produce audit log entries") cannot be satisfied for project operations. The protocol, both concrete classes, and all factory/dependency functions need updating.
- **#7**: All route handler dependency functions that instantiate repositories (`projects.py:47`, `effects.py:74`, `app.py:78`) must pass the AuditLogger from `app.state`. Without this, the AuditLogger instance exists but is never used — replicating the LRN-079 pattern of "wire call sites alongside parameter additions."

These two impacts should be treated as part of BL-060's implementation scope, not as separate features. They represent the full extent of wiring needed for audit logging to be functional.

## Cross-Version Impacts (backlog scope)

None identified. All impacts can be addressed within v009 scope.
