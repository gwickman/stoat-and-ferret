# Requirements: spa-routing

## Goal

Replace StaticFiles mount with catch-all route that serves both static files and SPA fallback for GUI sub-paths.

## Background

Backlog Item: BL-063

FastAPI serves the GUI via `StaticFiles(html=True)`, but this does not fall back to `index.html` for unknown sub-paths. Navigating directly to `/gui/library` or refreshing on `/gui/projects` returns 404. This was deferred from v005/01-frontend-foundation. The catch-all route must replace `StaticFiles` entirely because Starlette routes and mounts at the same path cannot coexist with fallthrough behavior.

## Functional Requirements

**FR-001: SPA fallback for GUI sub-paths**
- Direct navigation to `/gui/library`, `/gui/projects`, and other GUI sub-paths returns 200 with index.html content
- Acceptance: `GET /gui/library` returns 200 with HTML content from `gui/dist/index.html`

**FR-002: Static file serving**
- Requests for static assets (e.g., `/gui/assets/main.js`) return the correct file content
- Acceptance: `GET /gui/assets/main.js` returns the JavaScript file, not index.html

**FR-003: Bare /gui path**
- `GET /gui` returns index.html content
- Acceptance: `GET /gui` returns 200 with HTML content from `gui/dist/index.html`

**FR-004: Page refresh preservation**
- Page refresh on any GUI sub-path preserves the current view
- Acceptance: Refreshing on `/gui/projects` reloads the projects page

**FR-005: Conditional activation**
- SPA fallback routes only activate when `gui/dist/` directory exists (LRN-020)
- Acceptance: Without `gui/dist/`, no `/gui/*` routes are registered

**FR-006: Remove StaticFiles mount**
- The existing `app.mount("/gui", StaticFiles(...))` is removed and replaced by the catch-all routes
- Acceptance: No `StaticFiles` mount exists at `/gui` path

## Non-Functional Requirements

**NFR-001: No API route interference**
- SPA routes are registered after all API routers — API endpoints remain unaffected
- Metric: All existing API endpoint tests continue to pass

## Out of Scope

- Modifying React Router configuration
- Adding new GUI pages or routes
- E2E test updates for direct navigation (tracked separately)
- Content-type negotiation for static files beyond FileResponse defaults

## Test Requirements

- Unit: Verify `/gui/library` returns 200 with index.html content (AC1)
- Unit: Verify `/gui/projects` returns 200 with index.html content (AC1)
- Unit: Verify arbitrary `/gui/any-sub-path` returns SPA content (AC1)
- Unit: Verify static asset requests return correct file content (not index.html)
- Unit: Verify `/gui` bare path returns index.html
- Unit: Verify SPA fallback only activates when `gui/dist/` exists (LRN-020)
- Integration: Verify page refresh on GUI sub-path preserves current view (AC2)

See `comms/outbox/versions/design/v009/005-logical-design/test-strategy.md` for full test strategy.

## Reference

See `comms/outbox/versions/design/v009/004-research/` for supporting evidence.