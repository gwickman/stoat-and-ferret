# Theme Retrospective: 03-gui-components

## Theme Summary

Theme 03 delivered the four main GUI panels that form the user-facing frontend of the application: an application shell with navigation, a dashboard panel, a library browser, and a project manager. These components consume the infrastructure from Theme 01 (frontend scaffolding, WebSocket) and backend services from Theme 02 (thumbnails, pagination).

All four features completed successfully with every acceptance criterion passing (20/20) and all quality gates green across both Python and TypeScript toolchains.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Status |
|---|---------|------------|---------------|--------|
| 001 | application-shell | 6/6 PASS | ruff: PASS, mypy: PASS, pytest: PASS, vitest: PASS, tsc: PASS | Complete |
| 002 | dashboard-panel | 4/4 PASS | ruff: PASS, mypy: PASS, pytest: PASS, vitest: PASS, tsc: PASS | Complete |
| 003 | library-browser | 5/5 PASS | ruff: PASS, mypy: PASS, pytest: PASS, vitest: PASS | Complete |
| 004 | project-manager | 5/5 PASS | ruff: PASS, mypy: PASS, pytest: PASS, vitest: PASS | Complete |

**Final test suite:** 627 Python tests passed (93.26% coverage), 85 Vitest tests passed across 20 test files.

## Deliverables

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Shell layout with header, content, footer | Complete | Flex layout with router outlet |
| Tab navigation with React Router | Complete | `/gui` basename, progressive disclosure |
| Health indicator (green/yellow/red) | Complete | Polls `/health/ready` every 30s |
| WebSocket hook with auto-reconnect | Complete | Exponential backoff: 1s to 30s max |
| Dashboard health cards | Complete | Python API, Rust Core, FFmpeg status |
| Real-time activity log | Complete | WebSocket event subscription via Zustand |
| Metrics cards | Complete | Prometheus text parser for request count/duration |
| Video grid with thumbnails | Complete | Responsive CSS Grid layout |
| Search with 300ms debounce | Complete | Generic `useDebounce` hook |
| Sort controls (date/name/duration) | Complete | Client-side sorting after fetch |
| Scan modal with progress | Complete | Polling at 1s intervals for job status |
| Pagination for large libraries | Complete | Offset/limit with page controls |
| Project list with creation modal | Complete | Resolution/fps/format validation |
| Project details with timeline positions | Complete | Rust-calculated clip positions |
| Delete confirmation dialog | Complete | Confirm/cancel pattern |

## Key Decisions

### Pagination over virtual scrolling
**Context:** The theme design mentioned evaluating `tanstack-virtual` for large libraries (R-6).
**Choice:** Used standard offset/limit pagination with page controls instead of virtual scrolling.
**Outcome:** Simpler implementation that matches the backend API pattern. For typical libraries (<500 videos), pagination at 20 items/page is sufficient. Virtual scrolling can be added later if needed.

### Client-side sorting
**Context:** The backend list endpoint doesn't support sort parameters.
**Choice:** Applied sorting client-side after fetching results.
**Outcome:** Works well for paginated page sizes. For server-side sorting across the full dataset, the backend API would need sort parameter support.

### Separate WebSocket connections
**Context:** Both the Shell and DashboardPage need WebSocket access.
**Choice:** The DashboardPage creates its own WebSocket connection for the activity log, separate from the Shell's connection for the status bar.
**Outcome:** Functional but creates two concurrent connections to the same endpoint. A shared connection via context or store would be more efficient.

### Zustand for state management
**Context:** Multiple components need shared state (activity events, library filters, project selection).
**Choice:** Three Zustand stores: `activityStore`, `libraryStore`, `projectStore`.
**Outcome:** Clean separation of concerns with lightweight state management. The activity store uses a 50-entry FIFO eviction policy to prevent unbounded growth.

### Scan polling over WebSocket events
**Context:** The scan modal needs to track scan job progress.
**Choice:** Used `setInterval` polling at 1s intervals instead of subscribing to WebSocket events.
**Outcome:** Simpler implementation. WebSocket-based progress updates could be added as an enhancement for lower latency.

## Metrics

- **Files changed:** 61 (55 created, 6 modified)
- **Lines added/removed:** +4,225 / -130
- **New Vitest tests:** 85 total (28 shell + 18 dashboard + 19 library + 20 project manager)
- **Commits:** 4 (d6f93f9, 358653a, cd03e00, 2cf1eae)

## Learnings

### What Went Well
- The application shell's progressive disclosure and router setup provided a solid foundation that all subsequent features plugged into seamlessly via `<Outlet />`
- The handoff document from feature 001 effectively communicated integration points (WebSocket hook API, layout patterns, page component conventions) to downstream features
- Zustand stores kept state management lightweight and testable without the boilerplate of heavier alternatives
- All four features maintained green quality gates throughout, including both Python backend and TypeScript frontend toolchains
- The generic `useDebounce` hook created for the library browser is reusable across other features

### What Could Improve
- Dual WebSocket connections (Shell + Dashboard) are wasteful; a shared connection via React context or a Zustand store would be cleaner
- Client-side sorting only works within the current page, not across the full dataset; server-side sort support should be considered
- No quality-gaps.md files were generated for any features, which would have been useful for tracking minor debt items systematically

## Technical Debt

- **Dual WebSocket connections:** The Shell and DashboardPage each open their own WebSocket connection. These should be consolidated into a single shared connection managed at the app level.
- **Client-side sorting limitation:** Sort only applies within the current page of results. When libraries grow large, server-side sort parameters should be added to the backend API.
- **Scan progress polling:** The 1s polling interval for scan job status could be replaced with WebSocket-based progress events for lower latency and reduced server load.
- **Rust Core health inference:** The dashboard infers Rust Core health from the overall health status since there is no dedicated Rust health check endpoint. Adding a specific Rust health check would improve accuracy.
- **Search vs list total semantics:** Inherited from Theme 02 - the search endpoint `total` field returns result count while the list endpoint returns true total count. These should be aligned.

## Recommendations

1. **Consolidate WebSocket connections:** Before adding more real-time features, refactor to a single shared WebSocket connection with event routing to subscribers.
2. **Server-side sorting:** Add sort parameter support to the backend list endpoint to enable correct sorting across paginated results.
3. **E2E testing readiness:** All four GUI panels are now complete and ready for Theme 04 (E2E tests). The component test suite provides a solid unit-level foundation.
4. **Accessibility:** No accessibility testing was performed in this theme. Consider adding ARIA attributes and keyboard navigation support.
5. **Error boundaries:** Consider adding React error boundaries around each page component to prevent a failure in one panel from crashing the entire application.
