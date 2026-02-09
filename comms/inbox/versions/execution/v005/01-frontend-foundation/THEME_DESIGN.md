# THEME_DESIGN - 01: Frontend Foundation

## Goal

Scaffold the frontend project, configure static file serving from FastAPI, set up CI pipeline integration, and add WebSocket real-time event support. This is the infrastructure theme -- all subsequent GUI themes depend on it.

## Backlog Items

BL-003, BL-028, BL-029

## Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 001 | frontend-scaffolding | Scaffold React/Vite/TypeScript project, FastAPI static serving, CI pipeline | BL-028, BL-003 | None |
| 002 | websocket-endpoint | /ws WebSocket endpoint with ConnectionManager, broadcasting, correlation IDs | BL-029 | 001 |
| 003 | settings-and-docs | New settings fields, architecture/API/AGENTS doc updates | BL-003, BL-029 | 001, 002 |

## Dependencies

- **Inbound:** None (this is the first theme)
- **Outbound:** Theme 02 depends on settings fields from Feature 003. Theme 03 depends on frontend project and WebSocket from Features 001/002.

## Technical Approach

- **Frontend scaffolding:** `npm create vite@latest gui -- --template react-ts` with Tailwind CSS. Vite dev proxy routes `/api/*`, `/health/*`, `/metrics`, `/ws` to FastAPI. Production build to `gui/dist/` with `base: '/gui/'`.
- **Static file serving:** `StaticFiles(directory="gui/dist", html=True)` mounted after all API routers. `SPAStaticFiles` subclass available as fallback if `html=True` is insufficient.
- **CI:** Separate `frontend` job on ubuntu-latest with `node_modules` caching. Runs `npm ci`, `npm run build`, `npx vitest run`. Parallel to existing Python test matrix.
- **WebSocket:** ConnectionManager class with `connect()`, `disconnect()`, `broadcast()` methods. Injected via `create_app(ws_manager=...)` following LRN-005. Event types: health status changes, activity events (scan started/completed, project created). Correlation IDs from existing middleware.
- **Settings:** New Pydantic fields in Settings class: `thumbnail_dir`, `gui_static_path`, `ws_heartbeat_interval`.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R-1: Framework selection | Eliminated | React confirmed via design doc analysis |
| R-2: SPA routing edge cases | Medium | `html=True` sufficient for flat routes; `SPAStaticFiles` fallback documented |
| R-5: CI build time | Low | Caching, parallel jobs, ubuntu-only |

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md` for details.