# THEME_DESIGN - 03: GUI Components

## Goal

Build the four main GUI panels: application shell with navigation, dashboard, library browser, and project manager. These are the user-facing features that consume the infrastructure and backend services from Themes 01-02.

## Backlog Items

BL-030, BL-031, BL-033, BL-035

## Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 001 | application-shell | App shell with navigation, health indicator, status bar, progressive tabs | BL-030 | Theme 01 complete |
| 002 | dashboard-panel | Dashboard with health cards, WebSocket activity log, metrics | BL-031 | 001, Theme 01 (WebSocket) |
| 003 | library-browser | Video grid, thumbnails, search, sort/filter, scan modal, virtual scrolling | BL-033 | 001, Theme 02 (thumbnails + pagination) |
| 004 | project-manager | Project list, creation modal, details view, delete confirmation | BL-035 | 001 (shell) |

## Dependencies

- **Inbound:** Theme 01 (frontend project, WebSocket), Theme 02 (thumbnails, pagination fix).
- **Outbound:** Theme 04 (E2E tests) depends on all GUI components.

## Technical Approach

- **Application shell:** React Router for URL routing between Dashboard, Library, Projects tabs. `useWebSocket` custom hook with auto-reconnect (exponential backoff). Health indicator polls `/health/ready` and displays green/yellow/red. Status bar shows WebSocket connection state. Progressive tab disclosure: only show tabs whose backends are available.
- **Dashboard:** Health cards from `/health/ready` response (Python, Rust core, FFmpeg status). Activity log subscribes to WebSocket events. Metrics cards from `/metrics` endpoint. Auto-refresh on configurable interval (default 30s).
- **Library browser:** Video grid with thumbnail images from `/api/videos/{id}/thumbnail`. Search bar with 300ms debounce calling `/api/videos/search`. Sort by date/name/duration. Scan modal triggers `/api/v1/jobs` scan endpoint. Virtual scrolling or pagination for 100+ video libraries (R-6: evaluate tanstack-virtual, pagination fallback).
- **Project manager:** Project list from `/api/v1/projects`. New Project modal with resolution/fps/format validation. Details view shows clips with Rust-calculated timeline positions. Delete with confirmation dialog.
- **State management:** Zustand stores for app state, WebSocket connection, API data caching.
- **Testing:** Vitest unit tests for all components with mock API responses.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R-3: WebSocket stability | Medium | Local app, 30s heartbeat, client-side auto-reconnect |
| R-6: Virtual scrolling compatibility | Low | Pagination fallback per BL-033 AC#5 |

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md` for details.