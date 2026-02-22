# Theme: gui-runtime-fixes

## Goal

Fix three runtime gaps in the GUI and API layer: SPA routing fallback for direct navigation, correct pagination totals for the projects endpoint, and WebSocket broadcast calls for real-time event delivery to the frontend.

## Design Artifacts

See `comms/outbox/versions/design/v009/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | spa-routing | BL-063 | Replace StaticFiles mount with catch-all route serving both static files and SPA fallback |
| 002 | pagination-fix | BL-064 | Add count() to AsyncProjectRepository, fix total in API, and add frontend pagination UI |
| 003 | websocket-broadcasts | BL-065 | Wire broadcast() into scan service and project router for real-time WebSocket events |

## Dependencies

- No dependencies on Theme 1 (functionally independent, sequenced after Theme 1 for code-conflict avoidance)
- Features are sequenced by priority and complexity (001 P1, 002 P2, 003 P2 highest complexity last)

## Technical Approach

- **001-spa-routing:** Remove `StaticFiles` mount at `/gui`. Add `@app.get("/gui/{path:path}")` and `@app.get("/gui")` routes that serve files if they exist, otherwise serve `index.html`. Routes are conditional on `gui_dir.is_dir()`. See `006-critical-thinking/investigation-log.md` Investigation 3 for route-vs-mount evidence.
- **002-pagination-fix:** Add `count()` to `AsyncProjectRepository` protocol, SQLite, and InMemory implementations (mirroring `AsyncVideoRepository` pattern). Wire into projects router. Add `page`/`pageSize` state to project store and pagination UI to ProjectsPage following Library page pattern. See `004-research/codebase-patterns.md` Section 4 for count() pattern.
- **003-websocket-broadcasts:** Add `broadcast(build_event(...))` for PROJECT_CREATED in projects router, SCAN_STARTED/SCAN_COMPLETED in scan job handler. Access `ws_manager` via `request.app.state.ws_manager`. Defer HEALTH_STATUS trigger identification. See `006-critical-thinking/investigation-log.md` Investigation 2 for broadcast insertion points.

## Risks

| Risk | Mitigation |
|------|------------|
| SPA route intercepts static asset requests | Dual-purpose handler checks file existence first — see 006-critical-thinking/risk-assessment.md |
| Pagination scope increase (BL-064) | Follow proven Library page pattern — see 006-critical-thinking/risk-assessment.md |
| WebSocket broadcasts touch multiple routers | Reduced to 1 router + scan service — see 006-critical-thinking/risk-assessment.md |