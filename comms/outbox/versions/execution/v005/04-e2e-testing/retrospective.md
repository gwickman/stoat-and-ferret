# Theme Retrospective: 04-e2e-testing

## Theme Summary

Theme 04 established Playwright E2E testing infrastructure and delivered a test suite covering the four main user flows: tab navigation, library scan trigger, project creation, and WCAG AA accessibility checks. This is the final theme in v005, validating the full stack (FastAPI backend + built React frontend) end-to-end.

Both features completed successfully with all acceptance criteria passing (9/9) and all quality gates green across Python, TypeScript, and Playwright toolchains.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Status |
|---|---------|------------|---------------|--------|
| 001 | playwright-setup | 5/5 PASS | ruff: PASS, mypy: PASS, pytest: PASS, vitest: PASS | Complete |
| 002 | e2e-test-suite | 4/4 PASS | ruff: PASS, mypy: PASS, pytest: PASS, vitest: PASS, playwright: PASS | Complete |

**Final test suite:** 627 Python tests (93.28% coverage), 85 Vitest tests (20 files), 7 Playwright E2E tests.

## Deliverables

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Playwright config with webServer | Complete | Auto-starts FastAPI via `uvicorn --factory` |
| CI `e2e` job on ubuntu-latest | Complete | Browser caching, HTML report artifact |
| Chromium browser caching in CI | Complete | `actions/cache` for browser binaries |
| CI-specific test settings | Complete | `retries: 2`, `workers: 1`, `forbidOnly: true` |
| Navigation E2E test | Complete | Tab switching between Dashboard, Library, Projects |
| Scan trigger E2E test | Complete | Verifies progress/error feedback |
| Project creation E2E test | Complete | Modal open, form fill, submit, verify in list |
| WCAG AA accessibility checks | Complete | axe-core checks on all three main views |
| SortControls accessibility fix | Complete | Added `aria-label` to fix WCAG 4.1.2 violation |

## Key Decisions

### Client-side routing for E2E navigation
**Context:** E2E tests needed to navigate between Dashboard, Library, and Projects tabs.
**Choice:** Navigated via clicking tab elements starting from `/gui/` rather than direct URL navigation to sub-paths.
**Outcome:** Correct approach since the FastAPI `StaticFiles` mount doesn't handle SPA fallback routing for sub-paths like `/gui/library`. Tests accurately reflect how users navigate the application.

### Auto-loading gui_static_path in create_app()
**Context:** Playwright's `webServer` starts FastAPI via `uvicorn --factory`, but the factory function didn't serve the built frontend by default.
**Choice:** Modified `create_app()` to auto-load `gui_static_path` from settings when not explicitly provided.
**Outcome:** Enabled `uvicorn --factory` to serve the built frontend without extra arguments, making both Playwright and manual development use seamless.

### Chromium-only browser testing
**Context:** Cross-browser testing (Firefox, WebKit) would increase CI time and complexity.
**Choice:** Scoped to Chromium only for v005, as specified in the theme design.
**Outcome:** Keeps CI fast while covering the primary browser engine. Cross-browser can be added in a future version if needed.

### Scan test accepts any feedback state
**Context:** The scan test triggers a scan on a directory that may not exist in the test environment.
**Choice:** Verified that feedback appears (progress, complete, or error) rather than asserting a specific success outcome.
**Outcome:** Makes the test resilient across environments while still verifying the full scan trigger flow.

## Metrics

- **Files created:** 7 (config, 4 E2E specs, smoke test, gitignore entries)
- **Files modified:** 5 (package.json, package-lock.json, vitest.config.ts, ci.yml, app.py, SortControls.tsx)
- **New E2E tests:** 7 Playwright tests across 5 spec files
- **Commits:** 2 (c3c66d7, 758db32)

## Learnings

### What Went Well
- The Playwright `webServer` configuration provides a clean way to test the full stack without manual server management
- Browser caching in CI via `actions/cache` keeps E2E job times reasonable
- The accessibility testing with `@axe-core/playwright` caught a real WCAG 4.1.2 violation in SortControls that was fixed immediately, validating the value of automated accessibility checks
- The handoff document from feature 001 clearly communicated the test infrastructure setup, making feature 002 implementation straightforward
- Separating the E2E CI job from the main test matrix (ubuntu-only) avoids unnecessary cross-platform E2E overhead

### What Could Improve
- No SPA fallback routing means E2E tests can't navigate directly to sub-paths via URL; this limits test isolation since tests must navigate from the root
- The scan test is environment-dependent (the test directory may not exist), which could make it less deterministic
- No quality-gaps.md files were generated for either feature, which would help track minor issues systematically

## Technical Debt

- **SPA fallback routing:** The FastAPI `StaticFiles` mount doesn't handle SPA client-side routing for deep links like `/gui/library`. This means bookmarks and direct URL access to sub-routes won't work. A catch-all route or middleware that serves `index.html` for unmatched `/gui/*` paths would fix this.
- **Dual WebSocket connections:** Inherited from Theme 03 - the Shell and DashboardPage each open separate WebSocket connections that should be consolidated.
- **E2E test coverage gaps:** WebSocket interactions are not tested E2E (mocked in unit tests only). Real WebSocket E2E tests would increase confidence in real-time features.

## Recommendations

1. **Add SPA fallback routing:** Implement a catch-all route for `/gui/*` paths that serves `index.html`, enabling direct URL navigation and improving E2E test isolation.
2. **Expand E2E coverage over time:** As new features are added, grow the E2E suite to cover critical user journeys. Consider adding visual regression testing with Playwright screenshots.
3. **Cross-browser testing:** Add Firefox and/or WebKit to the Playwright config in a future version to catch browser-specific issues.
4. **E2E performance budget:** Consider adding Playwright performance assertions (load time thresholds) to catch regressions early.
5. **WebSocket E2E tests:** Add E2E tests that exercise real WebSocket connections to validate real-time event flows end-to-end.
