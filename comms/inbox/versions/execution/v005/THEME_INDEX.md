# v005 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: frontend-foundation

**Path:** `comms/inbox/versions/execution/v005/01-frontend-foundation/`
**Goal:** Scaffold the frontend project, configure static file serving from FastAPI, set up CI pipeline integration, and add WebSocket real-time event support. This is the infrastructure theme -- all subsequent GUI themes depend on it.

**Features:**

- 001-frontend-scaffolding: _Feature description_
- 002-websocket-endpoint: _Feature description_
- 003-settings-and-docs: _Feature description_
### Theme 02: backend-services

**Path:** `comms/inbox/versions/execution/v005/02-backend-services/`
**Goal:** Add backend capabilities that the GUI components consume: thumbnail generation pipeline and pagination total count fix. These are backend-only changes that must land before the GUI panels that depend on them.

**Features:**

- 001-thumbnail-pipeline: _Feature description_
- 002-pagination-total-count: _Feature description_
### Theme 03: gui-components

**Path:** `comms/inbox/versions/execution/v005/03-gui-components/`
**Goal:** Build the four main GUI panels: application shell with navigation, dashboard, library browser, and project manager. These are the user-facing features that consume the infrastructure and backend services from Themes 01-02.

**Features:**

- 001-application-shell: _Feature description_
- 002-dashboard-panel: _Feature description_
- 003-library-browser: _Feature description_
- 004-project-manager: _Feature description_
### Theme 04: e2e-testing

**Path:** `comms/inbox/versions/execution/v005/04-e2e-testing/`
**Goal:** Establish Playwright E2E test infrastructure with CI integration, covering navigation, scan trigger, project creation, and WCAG AA accessibility checks.

**Features:**

- 001-playwright-setup: _Feature description_
- 002-e2e-test-suite: _Feature description_
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
