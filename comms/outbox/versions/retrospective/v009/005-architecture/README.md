# 005 Architecture Alignment: v009

Architecture drift detected. C4 documentation was last generated for v008 and does not reflect 5 specific changes introduced by v009's 6 features across 2 themes. A new backlog item (BL-069) was created to track remediation.

## Existing Open Items

None. No open backlog items with architecture, C4 tags or search terms were found.

## Changes in v009

v009 delivered 2 themes with 6 features:

**Theme 01: Observability Pipeline** (3 features)
- Wired `ObservableFFmpegExecutor` into DI, wrapping `RealFFmpegExecutor` with Prometheus metrics and structured logging
- Wired `AuditLogger` into repository DI with a separate synchronous SQLite connection (WAL mode)
- Added `RotatingFileHandler` to `configure_logging()` for file-based log persistence (10MB rotation, 5 backups)

**Theme 02: GUI Runtime Fixes** (3 features)
- Replaced `StaticFiles` mount with catch-all FastAPI routes for SPA fallback
- Added `count()` to `AsyncProjectRepository` protocol and implementations for accurate pagination
- Wired `ConnectionManager.broadcast()` into project creation and scan handler for real-time WebSocket events

## Documentation Status

| Document | Exists | Generated For | Notes |
|----------|--------|---------------|-------|
| docs/C4-Documentation/README.md | Yes | v008 | Last updated 2026-02-22, delta mode |
| docs/C4-Documentation/c4-context.md | Yes | v008 | References "As of v008" in description |
| docs/C4-Documentation/c4-container.md | Yes | v008 | Detailed container/interface docs |
| docs/C4-Documentation/c4-component-*.md | Yes (8 files) | v008 | Component-level docs for all major components |
| docs/C4-Documentation/c4-code-*.md | Yes (36 files) | v008 | Code-level docs |
| docs/ARCHITECTURE.md | No | N/A | Does not exist |

C4 documentation is comprehensive but one version behind. The v009 retrospective explicitly notes: "C4 architecture documentation regeneration was attempted but failed for this version."

## Drift Assessment

5 drift items detected, all verified against source code:

1. **configure_logging() file rotation not documented**: C4 Data Access component describes logging as "JSON/console logging setup" but `configure_logging()` now accepts a `log_dir` parameter and adds a `RotatingFileHandler` (src/stoat_ferret/logging.py:18-21,78-80).

2. **Project Repository missing count()**: C4 Data Access lists Project Repository operations as "add, get, list_projects, update, delete" but `count()` now exists on the protocol and both implementations (src/stoat_ferret/db/project_repository.py:87,190,254).

3. **SPA routing pattern incorrect**: C4 API Gateway states "GUI static files mounted at /gui" (implying StaticFiles) but the implementation uses `@app.get("/gui")` and `@app.get("/gui/{path:path}")` catch-all routes with file-existence checks and SPA fallback (src/stoat_ferret/api/app.py:206-211).

4. **DI wiring for ObservableFFmpegExecutor and AuditLogger not reflected**: These components existed in v008 as documented code but were not wired into the application lifespan. They are now actively created and stored on `app.state` during startup (src/stoat_ferret/api/app.py:86-94).

5. **WebSocket broadcasts now actively wired**: v008 C4 listed event types (SCAN_STARTED, SCAN_COMPLETED, PROJECT_CREATED) but broadcast() calls were not connected. v009 wired broadcast calls in the scan handler (src/stoat_ferret/api/services/scan.py:84,94) and project creation router (src/stoat_ferret/api/routers/projects.py:150).

## Action Taken

Created new backlog item **BL-069** ("Update C4 architecture documentation for v009 changes", P2, tags: architecture/c4/documentation) with 5 acceptance criteria mapping to each drift item. No existing open architecture item existed to update.
