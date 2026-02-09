# THEME_DESIGN - 04: E2E Testing

## Goal

Establish Playwright E2E test infrastructure with CI integration, covering navigation, scan trigger, project creation, and WCAG AA accessibility checks.

## Backlog Items

BL-036

## Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 001 | playwright-setup | Playwright config, CI integration, webServer for FastAPI, browser caching | BL-036 | Theme 03 complete |
| 002 | e2e-test-suite | E2E tests for navigation, scan, project creation, WCAG AA accessibility | BL-036 | 001 |

## Dependencies

- **Inbound:** Theme 03 complete (all GUI components must exist for meaningful E2E tests).
- **Outbound:** None (final theme).

## Technical Approach

- **Playwright setup:** `npm init playwright@latest` in `gui/`. Config with `webServer` pointing to FastAPI (`uvicorn` with `--factory`). `baseURL: 'http://localhost:8000/gui/'`. Browser installation cached in CI via `actions/cache`.
- **CI integration:** Separate `e2e` job on ubuntu-latest only (not full OS matrix per R-5 mitigation). Installs browsers, builds frontend, runs E2E tests. HTML report uploaded as artifact. Parallel to existing test matrix.
- **E2E test suite:** Navigation between Dashboard/Library/Projects tabs. Scan trigger from library browser. Project creation flow (modal -> form -> submit -> verify). WebSocket mock via `page.routeWebSocket()` for deterministic testing.
- **Accessibility:** `@axe-core/playwright` with `withTags(['wcag2a', 'wcag2aa'])` on each main view.
- **Test config:** `fullyParallel: true`, `retries: 2` in CI, `workers: 1` in CI, `trace: 'on-first-retry'`.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R-5: CI build time | Low | ubuntu-only, browser caching, parallel job |
| UQ-4: Frontend coverage | Low | No enforced threshold in v005; baseline after Theme 03 |

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md` for details.