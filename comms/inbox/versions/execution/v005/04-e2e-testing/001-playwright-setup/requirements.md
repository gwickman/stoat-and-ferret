# Requirements - 001: Playwright Setup

## Goal

Configure Playwright with CI integration on ubuntu-latest, `webServer` config for FastAPI, and browser installation with caching.

## Background

The design docs (`docs/design/08-gui-architecture.md`) specify Playwright for E2E testing, but no E2E test infrastructure exists. Unit tests (Vitest) cover individual components, but there are no tests verifying the full stack (FastAPI + built frontend) works end-to-end. This feature sets up the infrastructure; Feature 002 writes the actual tests.

**Backlog Item:** BL-036

## Functional Requirements

**FR-001: Playwright initialization**
Initialize Playwright in `gui/` with `npm init playwright@latest`. Configure `playwright.config.ts` with `testDir: './e2e'`, `fullyParallel: true`, and `trace: 'on-first-retry'`.
- AC: Playwright config file exists at `gui/playwright.config.ts` with correct settings

**FR-002: WebServer configuration**
Configure `webServer` in Playwright config to start FastAPI serving the built frontend. Use `uvicorn` with `--factory` flag. Health check URL: `http://localhost:8000/health/live`.
- AC: `npx playwright test` automatically starts FastAPI and waits for health check

**FR-003: CI workflow**
Add an `e2e` job to `.github/workflows/ci.yml` on ubuntu-latest only. Install browsers with caching. Build frontend before running tests. Upload HTML report as artifact.
- AC: CI `e2e` job runs Playwright tests on ubuntu-latest with browser caching

**FR-004: Browser installation**
Configure browser installation (Chromium at minimum) with `actions/cache` for CI caching of browser binaries.
- AC: Browser binaries are cached between CI runs, reducing install time

**FR-005: Test configuration**
Configure CI-specific settings: `retries: 2`, `workers: 1`, `forbidOnly: true`.
- AC: Playwright config uses CI-appropriate settings when `CI` env var is set

## Non-Functional Requirements

**NFR-001: CI job time**
E2E CI job completes within 5 minutes including browser installation, frontend build, and test execution.
- Metric: Total `e2e` job time < 5 minutes with cached browsers

## Out of Scope

- Cross-browser testing (Chromium only for v005)
- Visual regression testing
- Performance testing via Playwright
- Mobile viewport testing

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Integration tests | Playwright `webServer` starts FastAPI and serves built frontend; browser navigates to `/gui/` successfully |
| CI tests | GitHub Actions workflow installs browsers, builds frontend, runs E2E |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.