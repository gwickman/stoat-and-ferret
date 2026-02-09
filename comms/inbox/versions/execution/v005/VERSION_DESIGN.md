# v005 Version Design

## Overview

**Version:** v005
**Title:** GUI Shell, Library Browser & Project Manager. Build the frontend from scratch: create a React/TypeScript/Vite frontend project, add WebSocket support for real-time events, build the application shell with navigation, implement library browser with thumbnail generation, and create the project manager. Completes Phase 1 (Milestones M1.10-M1.12).
**Themes:** 4

## Backlog Items

- [BL-003](docs/auto-dev/BACKLOG.md#bl-003)
- [BL-028](docs/auto-dev/BACKLOG.md#bl-028)
- [BL-029](docs/auto-dev/BACKLOG.md#bl-029)
- [BL-030](docs/auto-dev/BACKLOG.md#bl-030)
- [BL-031](docs/auto-dev/BACKLOG.md#bl-031)
- [BL-032](docs/auto-dev/BACKLOG.md#bl-032)
- [BL-033](docs/auto-dev/BACKLOG.md#bl-033)
- [BL-034](docs/auto-dev/BACKLOG.md#bl-034)
- [BL-035](docs/auto-dev/BACKLOG.md#bl-035)
- [BL-036](docs/auto-dev/BACKLOG.md#bl-036)

## Design Context

### Rationale

v005 is the first version introducing a user-facing GUI. All prior versions (v001-v004) built backend infrastructure: API, database, FFmpeg integration, job queue, and testing foundation. The frontend is greenfield with no existing code. Framework selection (React) was confirmed through design research. This version completes Phase 1 by delivering the GUI shell, library browser, and project manager.

### Constraints

- Frontend is greenfield - no existing frontend code or framework choice prior to v005
- Framework selection (BL-028) must be resolved first as all GUI work depends on it
- Static file serving (BL-003) is a prerequisite for serving the frontend from FastAPI
- WebSocket support was deferred from v003 and must be implemented for real-time features
- Playwright E2E tests require all GUI components to exist before meaningful tests can be written
- CI build time must be managed with caching and parallel jobs

### Assumptions

- React 18+ with TypeScript selected based on design document alignment and ecosystem analysis
- Zustand for state management as recommended in design docs
- StaticFiles(html=True) sufficient for flat v005 SPA routes
- On-scan thumbnail generation acceptable for v005 library sizes
- Playwright E2E runs on ubuntu-latest only, not full OS matrix

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-frontend-foundation | Scaffold the frontend project, configure static file serving from FastAPI, set up CI pipeline integration, and add WebSocket real-time event support. | 3 |
| 2 | 02-backend-services | Add backend capabilities that the GUI components consume: thumbnail generation pipeline and pagination total count fix. | 2 |
| 3 | 03-gui-components | Build the four main GUI panels: application shell with navigation, dashboard, library browser, and project manager. | 4 |
| 4 | 04-e2e-testing | Establish Playwright E2E test infrastructure with CI integration, covering navigation, scan trigger, project creation, and WCAG AA accessibility checks. | 2 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (frontend-foundation): Scaffold the frontend project, configure static file serving from FastAPI, set up CI pipeline integration, and add WebSocket real-time event support.
- [ ] Theme 02 (backend-services): Add backend capabilities that the GUI components consume: thumbnail generation pipeline and pagination total count fix.
- [ ] Theme 03 (gui-components): Build the four main GUI panels: application shell with navigation, dashboard, library browser, and project manager.
- [ ] Theme 04 (e2e-testing): Establish Playwright E2E test infrastructure with CI integration, covering navigation, scan trigger, project creation, and WCAG AA accessibility checks.
