# Theme 02: GUI Runtime Fixes — Retrospective

## Summary

Fixed three runtime gaps in the GUI and API layer: SPA routing fallback for direct navigation to GUI sub-paths, correct pagination totals for the projects endpoint (backend + frontend UI), and WebSocket broadcast calls for real-time event delivery. All three features were delivered successfully with all acceptance criteria passing and all quality gates green.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Status |
|---|---------|------------|---------------|--------|
| 001 | spa-routing | 6/6 pass | ruff, mypy, pytest pass | Complete |
| 002 | pagination-fix | 5/5 pass | ruff, mypy, pytest, tsc, vitest pass | Complete |
| 003 | websocket-broadcasts | 4/4 pass | ruff, mypy, pytest pass | Complete |

**Total:** 15/15 acceptance criteria passed across 3 features.

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| SPA routing fallback | Replaced `StaticFiles` mount with catch-all FastAPI routes that serve static files or fall back to `index.html` for client-side routing |
| Projects pagination | Added `count()` to project repository, wired true total into API response, added pagination state and UI to frontend |
| WebSocket broadcasts | Wired `ConnectionManager.broadcast()` into project creation and scan handler for `PROJECT_CREATED`, `SCAN_STARTED`, and `SCAN_COMPLETED` events |

## Key Decisions

### Replace StaticFiles with catch-all routes for SPA
**Context:** `StaticFiles` mount returns 404 for SPA sub-paths like `/gui/library` on direct navigation or page refresh.
**Choice:** Replace the mount with two FastAPI route handlers (`/gui` and `/gui/{path:path}`) that check for static files first and fall back to `index.html`.
**Outcome:** SPA routing works for all sub-paths while static assets continue to be served correctly. The conditional `gui_dir.is_dir()` guard is preserved.

### Mirror existing repository count pattern for projects
**Context:** `AsyncVideoRepository` already had a `count()` method, but `AsyncProjectRepository` did not. The projects endpoint was returning `len(projects)` (page size) as the total.
**Choice:** Add `count()` to the project repository protocol and both implementations (SQLite `SELECT COUNT(*)`, InMemory `len()`), matching the existing video repository pattern.
**Outcome:** Consistent repository API across both entity types; pagination total is accurate.

### Guard broadcasts with `if ws_manager:`
**Context:** WebSocket manager may not be available in all contexts (tests, minimal deployments).
**Choice:** Guard all broadcast calls with `if ws_manager:` to prevent crashes when the manager is not set.
**Outcome:** Broadcasts are a no-op when ws_manager is absent; no test infrastructure changes required for non-broadcast tests.

## Metrics

| Metric | Start (pre-theme) | End (post-theme) |
|--------|-------------------|-------------------|
| Tests passing | 910 | 936 |
| Test coverage | 92.89% | 92.92% |
| New test files | — | 2 (`test_spa_routing.py`, `test_websocket_broadcasts.py`) |
| Frontend tests | ~143 | 143 (vitest) |

## Learnings

### What Went Well
- All three features were tightly scoped runtime fixes with clear acceptance criteria, making each one fast to implement and verify.
- The existing patterns (repository protocol + implementations, `build_event()` for WebSocket events, DI via `app.state`) provided clear templates for each feature.
- Frontend changes in feature 002 followed the established `LibraryPage.tsx` pagination pattern, reducing design decisions.

### Patterns Discovered
- **SPA fallback pattern:** For FastAPI serving a frontend SPA, catch-all routes with file-existence checks are more flexible than `StaticFiles` mounts. The two-route approach (`/gui` + `/gui/{path:path}`) handles both bare paths and deep links.
- **Repository count pattern:** Adding `count()` to repository protocols is the standard way to support accurate pagination totals. Protocol, SQLite (`SELECT COUNT(*)`), and InMemory (`len()`) implementations are straightforward.
- **Broadcast guard pattern:** `if ws_manager:` guards on all broadcast calls allow WebSocket events to be optional without affecting core functionality or test setup.

## Technical Debt

| Item | Source | Severity | Notes |
|------|--------|----------|-------|
| No cache headers on static files | 001-spa-routing | Low | The catch-all route handler serves files without cache-control headers; `StaticFiles` may have provided these automatically |
| Pagination not on all list endpoints | 002-pagination-fix | Low | Projects endpoint now has full pagination; other list endpoints (videos) should be checked for consistency |
| No broadcast for project deletion | 003-websocket-broadcasts | Low | `PROJECT_CREATED` is broadcast but `PROJECT_DELETED` is not; frontend must poll or refresh to detect deletions |
| No integration test for live WebSocket broadcast | 003-websocket-broadcasts | Low | Broadcasts are tested via mocked `ws_manager`; no end-to-end WebSocket client test verifies actual message delivery |

## Recommendations

1. **For future SPA work:** The catch-all route pattern works well but consider adding cache-control headers for static assets to improve frontend load performance.
2. **For pagination consistency:** Apply the same `count()` + pagination pattern to any other list endpoints that may grow beyond a single page.
3. **For WebSocket expansion:** Add broadcast events for delete and update operations to complete the real-time event coverage. Consider a decorator or middleware pattern if broadcast calls become repetitive.
