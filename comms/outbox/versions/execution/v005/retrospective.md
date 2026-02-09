# v005 Version Retrospective

## Version Summary

**Version:** v005
**Title:** GUI Shell, Library Browser & Project Manager
**Status:** Complete
**Started:** 2026-02-09
**Completed:** 2026-02-09

v005 delivered the full frontend stack for stoat-and-ferret: a React/TypeScript/Vite frontend project scaffolded from scratch, WebSocket real-time event support, backend thumbnail generation and pagination fixes, four main GUI panels (application shell, dashboard, library browser, project manager), and Playwright E2E testing infrastructure. This completes Phase 1 milestones M1.10-M1.12.

All 4 themes and 11 features completed successfully with 100% acceptance criteria passing (38/38) and all quality gates green across Python, TypeScript, and Playwright toolchains.

## Theme Results

| # | Theme | Features | Acceptance | Quality Gates | Status |
|---|-------|----------|------------|---------------|--------|
| 01 | frontend-foundation | 3/3 | 18/18 PASS | All PASS | Complete |
| 02 | backend-services | 2/2 | 11/11 PASS | All PASS | Complete |
| 03 | gui-components | 4/4 | 20/20 PASS | All PASS | Complete |
| 04 | e2e-testing | 2/2 | 9/9 PASS | All PASS | Complete |

**Totals:** 11/11 features, 58/58 acceptance criteria, 0 failures.

## C4 Documentation

**Status:** Not attempted (skipped)

C4 architecture documentation regeneration was not performed for v005. The frontend scaffolding, WebSocket infrastructure, GUI components, and E2E testing additions represent significant architectural changes that should be captured in updated C4 documentation. This is noted as technical debt for a future version.

## Cross-Theme Learnings

### DI Pattern Scales Well
The `create_app()` kwargs pattern consistently scaled across all themes. New components (WebSocket manager, thumbnail service, GUI static path) plugged in cleanly without breaking existing tests or requiring refactoring.

### Feature Sequencing Was Correct
The theme ordering (infrastructure → backend services → GUI components → E2E testing) was validated by clean handoffs. Each theme built on the previous without rework. Handoff documents between features effectively communicated integration points.

### First-Pass Quality Gate Success
All 11 features passed quality gates on first iteration across all three toolchains (ruff/mypy/pytest, vitest/tsc, playwright). This indicates the implementation plans were detailed enough to execute cleanly.

### Zustand Over Heavier State Management
Choosing Zustand for state management across the GUI components kept the implementation lightweight and testable. Three focused stores (activity, library, project) provided clean separation of concerns.

### Accessibility Testing Caught Real Issues
The axe-core accessibility checks in Theme 04 caught a real WCAG 4.1.2 violation in SortControls (missing `aria-label`), validating the value of automated accessibility testing.

### Conditional Static Mount Pattern
The conditional StaticFiles mount (only when the directory exists) proved essential for test isolation — backend tests don't require a frontend build.

## Technical Debt Summary

### High Priority

1. **SPA Fallback Routing:** FastAPI `StaticFiles` doesn't handle client-side routing for deep links like `/gui/library`. Bookmarks and direct URL access to sub-routes won't work. Needs a catch-all route serving `index.html` for unmatched `/gui/*` paths. *(Theme 04)*

2. **Dual WebSocket Connections:** The Shell and DashboardPage each open separate WebSocket connections to the same endpoint. Should be consolidated into a single shared connection with event routing. *(Themes 03, 04)*

### Medium Priority

3. **Client-Side Sorting Limitation:** Sort only applies within the current page of results. Backend API needs sort parameter support for correct cross-page sorting. *(Theme 03)*

4. **Search vs List Total Semantics:** The search endpoint `total` returns result count while the list endpoint returns true total count. Should be aligned when search pagination is added. *(Themes 02, 03)*

5. **C4 Documentation Regeneration:** Architecture documentation was not updated for v005. Frontend, WebSocket, and GUI components need to be captured in C4 diagrams. *(Version-level)*

### Low Priority

6. **Scan Progress Polling:** 1s `setInterval` polling for scan job status could be replaced with WebSocket-based progress events. *(Theme 03)*

7. **Synchronous FFmpeg for Thumbnails:** Thumbnail generation blocks thread pool executor. Consider `asyncio.create_subprocess_exec` for non-blocking calls in large libraries. *(Theme 02)*

8. **Heartbeat Settings Wiring:** `ws_heartbeat_interval` settings field exists but wiring to the WebSocket endpoint should be verified. *(Theme 01)*

9. **Dev Proxy Maintenance:** Vite dev proxy routes must be manually updated when new API prefixes are added. *(Theme 01)*

10. **Rust Core Health Inference:** Dashboard infers Rust Core health from overall health status; a dedicated endpoint would improve accuracy. *(Theme 03)*

11. **E2E WebSocket Coverage:** WebSocket interactions are only tested via unit tests, not end-to-end. *(Theme 04)*

## Process Improvements

1. **Handoff documents work well:** Feature-to-feature handoff documents effectively communicated integration points and patterns. This practice should continue.

2. **Quality-gaps.md generation:** No quality-gaps.md files were generated across any of the 11 features. While this reflects clean implementations, having a structured debt tracking mechanism would be beneficial even for minor items.

3. **Cross-browser testing deferred:** Chromium-only E2E testing is pragmatic for v005 but should be expanded. Consider adding Firefox/WebKit in a future version.

## Statistics

| Metric | Value |
|--------|-------|
| Themes completed | 4/4 |
| Features completed | 11/11 |
| Acceptance criteria passed | 58/58 |
| PRs merged | ~11 |
| New Python tests | ~54 |
| New Vitest tests | 85 |
| New Playwright E2E tests | 7 |
| Final Python test count | 627 passed, 15 skipped |
| Python coverage | 93.28% |
| Vitest test files | 20 |
| Quality gate iterations | 1 per feature (all first-pass) |
| Total lines added | ~5,400+ |
| Total files created/modified | ~80+ |
