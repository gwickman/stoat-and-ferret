# Handoff: 001-playwright-setup -> 002 (next feature)

## What Was Done

Playwright E2E infrastructure is fully configured and ready for writing tests.

## Key Implementation Details

- **Playwright config**: `gui/playwright.config.ts` with `webServer` that starts FastAPI via `uv run uvicorn --factory`
- **Base URL**: Tests use `baseURL: 'http://localhost:8000/gui/'` - all `page.goto()` calls are relative to this
- **Health check**: WebServer waits for `http://localhost:8000/health/live` before running tests
- **GUI auto-serve**: `create_app()` now auto-loads `gui_static_path` from settings (default `gui/dist`), so `uvicorn --factory` serves the built frontend without extra args
- **Vitest exclusion**: The `e2e/` directory is excluded from Vitest via `vitest.config.ts`

## For Next Feature

- E2E tests go in `gui/e2e/*.spec.ts`
- Build frontend before running: `cd gui && npm run build && npx playwright test`
- The `@axe-core/playwright` package is installed for accessibility testing
- CI runs on ubuntu-latest only (Chromium); cross-browser is out of scope for v005
