# v008 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: application-startup-wiring

**Path:** `comms/inbox/versions/execution/v008/01-application-startup-wiring/`
**Goal:** Wire existing but disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence, so a fresh application start produces a fully functional system without manual intervention. All three features share the same modification point (`src/stoat_ferret/api/app.py` lifespan) and represent the same class of work: connecting infrastructure built in v002/v003 that was never wired.

**Features:**

- 001-database-startup: Wire create_tables() into lifespan so database schema is created automatically on startup
- 002-logging-startup: Call configure_logging() at startup and wire settings.log_level to control log verbosity
- 003-orphaned-settings: Wire settings.debug to FastAPI and settings.ws_heartbeat_interval to ws.py
### Theme 02: ci-stability

**Path:** `comms/inbox/versions/execution/v008/02-ci-stability/`
**Goal:** Eliminate the flaky E2E test that intermittently blocks CI merges, restoring reliable CI signal for all future development. During v007 execution, this flake caused a false-positive halt on the dynamic-parameter-forms feature despite all acceptance criteria passing.

**Features:**

- 001-flaky-e2e-fix: Fix toBeHidden() timeout in project-creation.spec.ts so E2E passes reliably
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
