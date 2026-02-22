# C4 Context Synthesis: stoat-and-ferret v008

Identified 3 personas, documented 12 system features, and created 3 user journeys for the stoat-and-ferret AI-driven video editor. This is a delta update from v007: the primary changes reflect v008's startup integrity improvements (database wiring, structured logging, configurable heartbeat and debug settings) and the stabilized E2E test suite.

## System Purpose

stoat-and-ferret is an AI-driven, non-destructive video editor providing a REST API and web GUI for managing video libraries, assembling editing projects, applying 9 built-in effects and transitions, and rendering output via FFmpeg.

## Personas Identified

3 personas:

1. **Editor User (Human)** -- Uses the web GUI to manage a video library, build editing projects, apply effects and transitions, and monitor system health via the dashboard.
2. **AI Agent (Programmatic)** -- Discovers the API via OpenAPI schema and AI hints, then drives editing workflows programmatically through REST calls. The API is deliberately designed for machine consumption.
3. **Developer / Maintainer (Human)** -- Builds, tests, and deploys the system across three technology stacks (Python, Rust, TypeScript) using CLI tools and GitHub Actions CI. In v008, dedicated test suites verify startup wiring for database creation, structured logging, and orphaned settings.

## Features Documented

12 features:

1. Video Library Management (scan, metadata extraction, thumbnails, full-text search)
2. Project Management (create projects, add/reorder clips, timeline calculation)
3. Effect Application (9 effects: text overlay, speed control, volume, audio fade, audio mix, audio ducking, video fade, crossfade with 59 transition types, audio crossfade)
4. Transition Application (between adjacent clips with adjacency validation)
5. Effect Discovery (parameter schemas, AI hints, filter previews)
6. Effect Workshop GUI (catalog, parameter forms, filter preview, clip selector, effect stack apply/edit/remove lifecycle)
7. Web Dashboard (health cards, metrics, WebSocket activity log with configurable heartbeat interval)
8. Video Library Browser GUI (search, sort, pagination, scan modal)
9. API Discovery (OpenAPI, Swagger UI, ReDoc)
10. Health Monitoring (liveness/readiness probes)
11. Observability (Prometheus metrics, structured logging wired at startup with configurable log level, correlation IDs, audit trail)
12. Async Job Processing (background job queue with status polling)

## User Journeys Created

3 journeys (one per persona):

1. **Editor: Import Videos and Build a Project with Effects** -- 13 steps from opening the GUI through scanning, project creation, effect application, and transition configuration.
2. **AI Agent: Discover Effects and Drive an Editing Workflow** -- 9 steps covering API discovery, effect catalog querying, project assembly, effect CRUD, and transition application.
3. **Developer: Quality Verification and Deployment** -- 8 steps covering toolchain setup, quality gates across all three stacks, CI pipeline, and merge workflow.

## External Dependencies

6 external dependencies:

1. **FFmpeg / ffprobe** (required) -- All video processing via subprocess
2. **Local Filesystem** (required) -- Source videos, database, thumbnails
3. **SQLite** (required, embedded) -- In-process database via aiosqlite; schema created automatically on startup via `create_tables()`
4. **Prometheus** (optional) -- Metrics collection via HTTP scrape
5. **GitHub Actions CI** (development) -- 9-matrix testing, Rust coverage, E2E Playwright tests (15 tests)
6. **Docker** (optional) -- Multi-stage containerized deployment

## Delta Changes from v007

The existing context document was accurate and required only targeted updates for v008:

- **Startup integrity**: Added mention of v008 startup wiring in the Long Description and Developer persona: database schema creation on first run (`create_tables()` wired into lifespan), structured logging configured at startup with `settings.log_level`, and orphaned settings `debug` and `ws_heartbeat_interval` wired to their consumers.
- **SQLite dependency**: Updated to note schema is created automatically on startup (not just migration-managed).
- **Web Dashboard feature**: Added "configurable heartbeat interval" to reflect `ws_heartbeat_interval` now wired.
- **Observability feature**: Updated to note structured JSON logs are "wired at startup with configurable log level".
- **Developer persona**: Added note that v008 introduced dedicated test suites (startup wiring, orphaned settings) to the persona description.
- **Developer journey step 7**: Updated E2E count from implied to explicit 15 tests, including WCAG AA and effect workshop lifecycle tests.
- **No persona or feature additions**: All 3 personas and 12 features carry forward from v007. v008 was a wiring/stability release, not a feature release.

## Sources Used

- `docs/C4-Documentation/c4-context.md` -- Existing v007 context document (baseline)
- `docs/C4-Documentation/c4-container.md` -- Container deployment architecture (updated for v008)
- `docs/C4-Documentation/c4-component.md` -- Component relationships
- `README.md` -- Project description and status (alpha)
- `AGENTS.md` -- Project structure, commands, coding standards, PR workflow
- `docs/auto-dev/PLAN.md` -- v008 goals, themes, and backlog items
- `tests/` directory -- Test names to verify feature coverage (startup, orphaned settings, logging, E2E specs)
