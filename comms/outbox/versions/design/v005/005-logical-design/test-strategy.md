# Test Strategy — v005

## Overview

v005 introduces two new test categories (frontend unit tests via Vitest, E2E tests via Playwright) alongside existing Python pytest tests. Each feature specifies its test requirements below.

---

## Theme 01: Frontend Foundation

### Feature 001: Frontend Scaffolding (`001-frontend-scaffolding`)

| Category | Requirements |
|----------|-------------|
| **Unit tests** | Vitest smoke test (default from `create-vite` template) passes |
| **Integration tests** | FastAPI serves `gui/dist/index.html` at `/gui/` route; API routes still respond correctly after static mount |
| **Contract tests** | Vite build produces `gui/dist/index.html` and asset files |

### Feature 002: WebSocket Endpoint (`002-websocket-endpoint`)

| Category | Requirements |
|----------|-------------|
| **Unit tests** | ConnectionManager: connect adds to set, disconnect removes, broadcast sends to all, dead connections cleaned up |
| **Integration tests** | WebSocket handshake at `/ws`; receive health status broadcast; receive activity event broadcast; correlation ID present in messages; reconnect after disconnect |
| **Contract tests** | WebSocket message schema validation (type, payload, correlation_id fields) |

### Feature 003: Settings and Docs (`003-settings-and-docs`)

| Category | Requirements |
|----------|-------------|
| **Unit tests** | New settings fields parse from env vars (`STOAT_THUMBNAIL_DIR`, `STOAT_GUI_STATIC_PATH`, `STOAT_WS_HEARTBEAT_INTERVAL`) |
| **Integration tests** | None (documentation updates) |

---

## Theme 02: Backend Services

### Feature 001: Thumbnail Pipeline (`001-thumbnail-pipeline`)

| Category | Requirements |
|----------|-------------|
| **Unit tests** | ThumbnailService: generates correct FFmpeg args, stores to configured dir, handles missing video gracefully, returns placeholder on extraction failure |
| **Integration tests** | `GET /api/videos/{id}/thumbnail` returns image for scanned video; returns placeholder for video without thumbnail; returns 404 for unknown video ID |
| **Contract tests** | FFmpeg command args match expected pattern via RecordingFFmpegExecutor (LRN-008); thumbnail response Content-Type is `image/jpeg` |

### Feature 002: Pagination Total Count (`002-pagination-total-count`)

| Category | Requirements |
|----------|-------------|
| **Unit tests** | `count()` returns correct total for SQLite and InMemory repositories; count reflects filters (if applicable) |
| **Integration tests** | `GET /api/v1/videos` response includes `total` field with true count; `GET /api/v1/videos/search` response includes `total` matching full result set, not page size |
| **Contract tests** | Response schema includes `total: int` field |

---

## Theme 03: GUI Components

### Feature 001: Application Shell (`001-application-shell`)

| Category | Requirements |
|----------|-------------|
| **Unit tests (Vitest)** | Navigation component renders all tabs; URL routing maps to correct panels; health indicator renders green/yellow/red based on mock API response; status bar shows WebSocket state |
| **Integration tests** | None (frontend-only; integration covered by E2E in Theme 04) |

### Feature 002: Dashboard Panel (`002-dashboard-panel`)

| Category | Requirements |
|----------|-------------|
| **Unit tests (Vitest)** | Health cards render component status from mock `/health/ready`; activity log appends WebSocket events; metrics cards display request count and timing from mock `/metrics`; auto-refresh triggers on interval |

### Feature 003: Library Browser (`003-library-browser`)

| Category | Requirements |
|----------|-------------|
| **Unit tests (Vitest)** | Video grid renders thumbnails with filename and duration; search bar triggers debounced API call; sort controls update grid ordering; scan modal renders and triggers scan API call; virtual scrolling renders visible items only |

### Feature 004: Project Manager (`004-project-manager`)

| Category | Requirements |
|----------|-------------|
| **Unit tests (Vitest)** | Project list renders name, date, clip count; creation modal validates resolution/fps/format inputs; details view displays clip list with timeline positions; delete button shows confirmation dialog; confirmed delete calls API |

---

## Theme 04: E2E Testing

### Feature 001: Playwright Setup (`001-playwright-setup`)

| Category | Requirements |
|----------|-------------|
| **Integration tests** | Playwright `webServer` starts FastAPI and serves built frontend; browser navigates to `/gui/` successfully |
| **CI tests** | GitHub Actions workflow installs browsers, builds frontend, runs E2E |

### Feature 002: E2E Test Suite (`002-e2e-test-suite`)

| Category | Requirements |
|----------|-------------|
| **E2E tests** | Navigation between Dashboard, Library, Projects tabs; scan trigger from library browser initiates scan and shows feedback; project creation flow (open modal, fill form, submit, verify in list) |
| **Accessibility** | `@axe-core/playwright` WCAG AA checks pass on each main view (dashboard, library, projects) |

---

## Test Infrastructure Summary

| Category | Tool | Location | Introduced By |
|----------|------|----------|---------------|
| Python unit/integration | pytest | `tests/` | Existing |
| Python contract tests | pytest + FakeFFmpegExecutor | `tests/` | Theme 02 |
| Frontend unit tests | Vitest | `gui/src/**/*.test.tsx` | Theme 01 |
| E2E tests | Playwright | `gui/e2e/**/*.spec.ts` | Theme 04 |
| Accessibility tests | @axe-core/playwright | `gui/e2e/accessibility.spec.ts` | Theme 04 |

## Coverage Thresholds

| Layer | Tool | Threshold | Notes |
|-------|------|-----------|-------|
| Python | pytest --cov | 80% | Existing; maintained |
| Rust | cargo test | 90% target (75% current) | Not in v005 scope |
| Frontend | Vitest --coverage | Start conservative (LRN-013) | Set baseline after Theme 03 |
