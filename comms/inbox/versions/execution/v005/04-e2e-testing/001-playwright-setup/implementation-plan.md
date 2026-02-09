# Implementation Plan - 001: Playwright Setup

## Overview

Initialize Playwright in the `gui/` project with a `webServer` configuration that starts FastAPI serving the built frontend. Add a separate `e2e` CI job on ubuntu-latest with browser caching and HTML report artifacts.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/playwright.config.ts` | Create | Playwright configuration with webServer and CI settings |
| `gui/e2e/` | Create | E2E test directory |
| `gui/e2e/example.spec.ts` | Create | Smoke test verifying frontend loads |
| `gui/package.json` | Modify | Add @playwright/test and @axe-core/playwright dev dependencies |
| `.github/workflows/ci.yml` | Modify | Add `e2e` job on ubuntu-latest |

## Implementation Stages

### Stage 1: Playwright Initialization

1. Install Playwright: `cd gui && npm install -D @playwright/test @axe-core/playwright`
2. Install browsers: `npx playwright install chromium`
3. Create `playwright.config.ts` with:
   - `testDir: './e2e'`
   - `fullyParallel: true`
   - `forbidOnly: !!process.env.CI`
   - `retries: process.env.CI ? 2 : 0`
   - `workers: process.env.CI ? 1 : undefined`
   - `reporter: 'html'`
   - `use: { baseURL: 'http://localhost:8000/gui/', trace: 'on-first-retry' }`
   - `projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]`
4. Configure `webServer`:
   - `command: 'cd .. && uv run uvicorn src.stoat_ferret.api.app:create_app --factory'`
   - `url: 'http://localhost:8000/health/live'`
   - `reuseExistingServer: !process.env.CI`
5. Create `gui/e2e/example.spec.ts` smoke test: navigate to `/gui/`, verify page title or heading

**Verification:**
```bash
cd gui && npm run build && npx playwright test
```

### Stage 2: CI Integration

1. Add `e2e` job to `.github/workflows/ci.yml`:
   - `runs-on: ubuntu-latest`
   - Setup Python + uv + Node.js
   - `uv sync` for backend dependencies
   - `cd gui && npm ci` for frontend dependencies
   - `cd gui && npm run build` to build frontend
   - Cache Playwright browsers via `actions/cache` with key based on Playwright version
   - `cd gui && npx playwright install chromium --with-deps`
   - `cd gui && npx playwright test`
   - Upload `gui/playwright-report/` as artifact on failure
2. Add `e2e` to `ci-status` job `needs` list

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Test Infrastructure Updates

- Playwright configured with webServer auto-start
- Browser binary caching in CI reduces install time
- HTML report uploaded as CI artifact for debugging failures

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
cd gui && npx playwright test
```

## Risks

- **R-5 (CI time):** E2E job runs on ubuntu-latest only, parallel to other jobs. Browser caching reduces install time. Monitor total CI time after merge.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: configure Playwright E2E testing with CI integration

- Initialize Playwright in gui/ with webServer config for FastAPI
- Configure chromium-only testing with CI-specific retries/workers
- Add e2e job to CI workflow on ubuntu-latest with browser caching
- Create smoke test verifying frontend loads from FastAPI

Implements BL-036 (setup portion)
```