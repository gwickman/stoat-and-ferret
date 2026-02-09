# Logical Design — v005: GUI Shell, Library Browser & Project Manager

## Version Overview

v005 delivers the first GUI layer for stoat-and-ferret: a React frontend served from FastAPI, WebSocket real-time events, application shell with navigation, library browser with thumbnails, project manager, and E2E test infrastructure. This completes Phase 1 (Milestones M1.10-M1.12).

**Goals:**
- Scaffold a React 18+ / TypeScript / Vite frontend project with CI integration
- Add WebSocket support for real-time event broadcasting
- Build the application shell, dashboard, library browser, and project manager
- Add thumbnail generation for the video library
- Fix pagination total count (tech debt from v003)
- Establish Playwright E2E test infrastructure

**Structure:** 4 themes, 13 features, covering all 10 backlog items.

---

## Theme 01: Frontend Foundation (`01-frontend-foundation`)

**Goal:** Scaffold the frontend project, configure static file serving from FastAPI, set up CI pipeline integration, and add WebSocket real-time event support. This is the infrastructure theme — all subsequent GUI themes depend on it.

**Backlog Items:** BL-003, BL-028, BL-029

| Feature | Name | Goal | Backlog | Dependencies |
|---------|------|------|---------|--------------|
| 001 | `001-frontend-scaffolding` | Scaffold React/Vite/TypeScript project in `gui/`, configure FastAPI static file serving, and update CI pipeline | BL-028, BL-003 | None |
| 002 | `002-websocket-endpoint` | Implement `/ws` WebSocket endpoint with ConnectionManager, event broadcasting, and correlation ID support | BL-029 | 001 (app factory changes) |
| 003 | `003-settings-and-docs` | Add new settings fields (thumbnail_dir, gui_static_path, ws_heartbeat_interval) and update architecture/API/AGENTS docs | BL-003, BL-029 | 001, 002 |

**Rationale:** BL-028 and BL-003 are tightly coupled — the frontend project and static file serving are inseparable. BL-029 (WebSocket) belongs here because it modifies the same app factory and lifespan that BL-003/BL-028 touch. Bundling them avoids repeated app.py modifications. Settings and documentation updates are collected into feature 003 to keep features 001 and 002 focused on code.

---

## Theme 02: Backend Services (`02-backend-services`)

**Goal:** Add backend capabilities that the GUI components consume: thumbnail generation pipeline and pagination total count fix. These are backend-only changes that must land before the GUI panels that depend on them.

**Backlog Items:** BL-032, BL-034

| Feature | Name | Goal | Backlog | Dependencies |
|---------|------|------|---------|--------------|
| 001 | `001-thumbnail-pipeline` | Implement thumbnail generation service using FFmpeg executor pattern, add GET /api/videos/{id}/thumbnail endpoint, and integrate with scan service | BL-032 | Theme 01 complete (settings fields) |
| 002 | `002-pagination-total-count` | Add `count()` to repository protocol, implement in SQLite and InMemory repositories, fix list/search endpoints to return true total | BL-034 | None (independent of Theme 01) |

**Rationale:** BL-032 (thumbnails) and BL-034 (pagination) are both backend-only prerequisites for the library browser (BL-033). Grouping them avoids interleaving backend and frontend work. BL-034 is a focused tech debt fix; BL-032 is a new service using established patterns (LRN-008 record-replay, LRN-005 constructor DI).

---

## Theme 03: GUI Components (`03-gui-components`)

**Goal:** Build the four main GUI panels: application shell with navigation, dashboard, library browser, and project manager. These are the user-facing features that consume the infrastructure and backend services from Themes 01-02.

**Backlog Items:** BL-030, BL-031, BL-033, BL-035

| Feature | Name | Goal | Backlog | Dependencies |
|---------|------|------|---------|--------------|
| 001 | `001-application-shell` | Build application shell with navigation tabs, health indicator, status bar, and progressive tab disclosure | BL-030 | Theme 01 complete |
| 002 | `002-dashboard-panel` | Build dashboard with health cards, real-time activity log via WebSocket, and metrics overview | BL-031 | 001 (shell provides layout), Theme 01 (WebSocket) |
| 003 | `003-library-browser` | Build library browser with video grid, thumbnails, search, sort/filter, scan modal, and virtual scrolling | BL-033 | 001 (shell), Theme 02 (thumbnails + pagination) |
| 004 | `004-project-manager` | Build project manager with list, creation modal, details view with timeline positions, and delete confirmation | BL-035 | 001 (shell) |

**Rationale:** All four panels share the same shell layout and routing. The application shell must come first — it provides the navigation frame. Dashboard depends on WebSocket (Theme 01). Library browser depends on thumbnails and pagination (Theme 02). Project manager only depends on the shell. Dashboard and project manager could theoretically parallelize after the shell, but sequential execution is simpler and avoids merge conflicts in shared layout files.

---

## Theme 04: E2E Testing (`04-e2e-testing`)

**Goal:** Establish Playwright E2E test infrastructure with CI integration, covering navigation, scan trigger, project creation, and WCAG AA accessibility checks.

**Backlog Items:** BL-036

| Feature | Name | Goal | Backlog | Dependencies |
|---------|------|------|---------|--------------|
| 001 | `001-playwright-setup` | Configure Playwright with CI integration, webServer config for FastAPI, and browser installation | BL-036 | Theme 03 complete (needs GUI components to test) |
| 002 | `002-e2e-test-suite` | Write E2E tests for navigation, scan trigger, project creation, and WCAG AA accessibility | BL-036 | 001 (Playwright configured) |

**Rationale:** E2E testing is isolated into its own theme because it tests the integrated system — all GUI components must exist before meaningful E2E tests can be written. Splitting into setup vs test authoring keeps each feature focused. The CI job for Playwright is part of setup (feature 001).

---

## Execution Order

### Theme Order

```
Theme 01: Frontend Foundation  →  Theme 02: Backend Services  →  Theme 03: GUI Components  →  Theme 04: E2E Testing
```

**Rationale:**
- **Theme 01 first** (LRN-019: infrastructure first): All GUI work depends on the frontend project, static file serving, and WebSocket. This is the foundation.
- **Theme 02 second**: Backend services (thumbnails, pagination fix) must be available before the library browser consumes them. These are backend-only changes that don't need the GUI shell.
- **Theme 03 third**: GUI components consume all prior infrastructure. Shell → Dashboard → Library → Project Manager is the natural order based on dependencies.
- **Theme 04 last**: E2E tests validate the integrated system. They need all components to exist.

### Feature Order Within Themes

**Theme 01:** 001 → 002 → 003 (linear; each depends on prior)
**Theme 02:** 001 → 002 (linear; thumbnail pipeline first for consistent ordering, though 002 is independent)
**Theme 03:** 001 → 002 → 003 → 004 (linear; shell first, then panels in dependency order)
**Theme 04:** 001 → 002 (linear; setup before test authoring)

### Dependency Graph

```
BL-028/BL-003 (frontend scaffolding)
    ├── BL-029 (WebSocket) ──── BL-031 (dashboard)
    ├── BL-030 (app shell) ──┬─ BL-031 (dashboard)
    │                        ├─ BL-033 (library browser)
    │                        ├─ BL-035 (project manager)
    │                        └─ BL-036 (E2E tests)
    └── BL-032 (thumbnails) ── BL-033 (library browser)
BL-034 (pagination fix) ────── BL-033 (library browser)
```

---

## Research Sources Adopted

| Decision | Source | Evidence Path |
|----------|--------|---------------|
| React 18+ with TypeScript over Svelte | RQ-1 analysis; design doc alignment (JSX in 08-gui-architecture.md) | `comms/outbox/versions/design/v005/004-research/external-research.md` §1 |
| Zustand for state management | Design doc recommendation (08-gui-architecture.md) | `comms/outbox/versions/design/v005/004-research/external-research.md` §1 |
| Vite with `react-ts` template | RQ-2; standard tooling | `comms/outbox/versions/design/v005/004-research/external-research.md` §2 |
| Dev proxy via `server.proxy` for API/WS | RQ-2; avoids CORS in development | `comms/outbox/versions/design/v005/004-research/external-research.md` §2 |
| `StaticFiles(html=True)` for SPA routing | RQ-3; FastAPI built-in SPA support | `comms/outbox/versions/design/v005/004-research/external-research.md` §3 |
| ConnectionManager pattern for WebSocket | RQ-4/5; injectable via `create_app()` (LRN-005) | `comms/outbox/versions/design/v005/004-research/external-research.md` §4 |
| FFmpeg `-ss 5 -frames:v 1` for thumbnails | RQ-6; integrates with existing executor pattern (LRN-008) | `comms/outbox/versions/design/v005/004-research/external-research.md` §5 |
| `count()` on repository protocol for pagination | RQ-10; minimal change to existing pattern | `comms/outbox/versions/design/v005/004-research/codebase-patterns.md` §Repository |
| Playwright with `webServer` and `@axe-core/playwright` | RQ-8/9; CI-friendly with accessibility | `comms/outbox/versions/design/v005/004-research/external-research.md` §6 |
| Thumbnail 320x180, JPEG quality 5, seek 5s | Evidence log concrete values | `comms/outbox/versions/design/v005/004-research/evidence-log.md` |
| WebSocket heartbeat 30s default | Evidence log; industry standard | `comms/outbox/versions/design/v005/004-research/evidence-log.md` |
| Search debounce 300ms | Evidence log; UI best practice | `comms/outbox/versions/design/v005/004-research/evidence-log.md` |

---

## Backlog Coverage

All 10 backlog items are mapped. No items deferred.

| Backlog | Theme | Feature(s) |
|---------|-------|------------|
| BL-003 | 01 | 001, 003 |
| BL-028 | 01 | 001 |
| BL-029 | 01 | 002, 003 |
| BL-030 | 03 | 001 |
| BL-031 | 03 | 002 |
| BL-032 | 02 | 001 |
| BL-033 | 03 | 003 |
| BL-034 | 02 | 002 |
| BL-035 | 03 | 004 |
| BL-036 | 04 | 001, 002 |
