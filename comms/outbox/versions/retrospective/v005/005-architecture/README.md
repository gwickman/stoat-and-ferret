# v005 Retrospective Task 005: Architecture Alignment

No additional architecture drift detected beyond what is already tracked in BL-018. The primary design document (`docs/design/02-architecture.md`) accurately reflects the high-level system architecture including the v005 additions (WebSocket endpoint, GUI static serving, frontend scaffolding). The missing gap remains C4-level documentation, which was already identified in the v004 retrospective and tracked as an open backlog item.

## Existing Open Items

- **BL-018**: "Create C4 architecture documentation" (P2, open, tags: documentation/architecture/c4). Updated with v005-specific notes documenting the new frontend components, services, and infrastructure that should be captured when C4 documentation is created.
- **BL-011**: "Consolidate Python/Rust build backends" (P3, open, tags: tooling/build/complexity). Related to architecture but not a documentation gap.

## Changes in v005

v005 ("GUI Shell, Library Browser & Project Manager") delivered 4 themes and 11 features:

**Theme 01 - Frontend Foundation:**
- React/TypeScript/Vite frontend scaffolded in `gui/` with Tailwind CSS v4
- FastAPI `StaticFiles` conditional mount at `/gui` (configurable via `STOAT_GUI_STATIC_PATH`)
- WebSocket endpoint `/ws` with `ConnectionManager`, heartbeat, correlation IDs, lazy dead-connection cleanup
- CI `frontend` job (vitest, tsc) running in parallel with Python matrix
- New settings: `thumbnail_dir`, `gui_static_path`, `ws_heartbeat_interval`

**Theme 02 - Backend Services:**
- `ThumbnailService` with FFmpeg-backed thumbnail generation (record-replay test pattern)
- `GET /api/v1/videos/{id}/thumbnail` endpoint with placeholder fallback
- `AsyncVideoRepository.count()` protocol method added to repository protocol
- Pagination total count fix (true total count vs page length)

**Theme 03 - GUI Components:**
- Application Shell with header/footer, tab navigation via React Router
- Dashboard panel with health cards, real-time activity log, Prometheus metrics display
- Library Browser with video grid, thumbnails, search (300ms debounce), sort controls, pagination, scan modal
- Project Manager with project list, creation modal (resolution/fps/format validation), delete confirmation
- Zustand state management: 3 stores (activityStore, libraryStore, projectStore)

**Theme 04 - E2E Testing:**
- Playwright configuration with `webServer` auto-starting FastAPI
- CI `e2e` job (ubuntu-only) with Chromium browser caching
- 7 E2E tests: navigation, scan trigger, project creation, WCAG AA accessibility (axe-core)
- SortControls accessibility fix (aria-label for WCAG 4.1.2)

## Documentation Status

| Document | Exists | Currency |
|----------|--------|----------|
| `docs/design/02-architecture.md` | Yes | Updated during v004; includes `/ws` and `/gui` endpoint groups, WebSocket transport layer, frontend static serving, and `gui/` directory structure. High-level architecture is current. |
| `docs/C4-Documentation/` | No | Never created. Tracked as BL-018. |
| `docs/ARCHITECTURE.md` | No | Does not exist (architecture lives in `docs/design/02-architecture.md`). |
| `docs/design/08-gui-architecture.md` | Yes | Created during v004 theme design for GUI architecture. |

## Drift Assessment

**No additional drift detected** beyond the already-tracked BL-018 gap.

The design document (`docs/design/02-architecture.md`) accurately captures the high-level system architecture:
- The Client Layer diagram includes "Web UI (React SPA)" as a client type
- The API Layer includes `/ws` (WebSocket) and `/gui` (static) endpoint groups
- The WebSocket Transport Layer section describes the ConnectionManager and event types
- The Frontend Static Serving section describes the conditional StaticFiles mount
- The directory structure includes the `gui/` tree with key files
- The DI pattern, repository protocol, and service layer patterns are documented

**Items at the component level not in the design doc** (appropriate for C4 documentation, not design doc):
1. Frontend component hierarchy (Shell, Dashboard, Library Browser, Project Manager)
2. Zustand store architecture (3 stores with specific responsibilities)
3. Playwright E2E infrastructure details
4. `ThumbnailService` as a standalone service (vs. Library Service sub-responsibility)
5. `GET /api/v1/videos/{id}/thumbnail` endpoint (not in endpoint groups table)

These are component-level details that belong in C4 Component/Code documentation, not in the high-level design doc. BL-018 already tracks this need.

## Action Taken

- Updated **BL-018** notes with v005-specific architectural additions that should be captured when C4 documentation is created
- No new backlog items needed; the existing BL-018 comprehensively covers the documentation gap
- The v005 version retrospective already documents C4 documentation as medium-priority technical debt (item #5)
