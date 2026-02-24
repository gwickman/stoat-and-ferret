# C4 Context Synthesis - Task 005 Results

## System Purpose

stoat-and-ferret is an AI-driven video editor with a REST API and web GUI. It enables human users and AI agents to scan local video directories into a searchable library, assemble editing projects from clips on a timeline, apply 9 built-in visual and audio effects, configure transitions between clips, and preview the FFmpeg filter strings that will produce the final output. The system is in alpha (v011), self-hosted, single-user, and not published to any package registry.

## Personas Identified: 4

1. **Editor User** (Human) -- Uses the web GUI to manage video libraries and build editing projects with effects and transitions.
2. **AI Agent** (Programmatic) -- Discovers the API via OpenAPI schema and drives editing operations programmatically using machine-readable effect catalogs with AI hints.
3. **Developer / Maintainer** (Human) -- Develops, tests, and deploys the system across Python, Rust, and TypeScript stacks; maintains cross-platform CI.
4. **auto-dev-mcp** (Programmatic) -- AI-driven development orchestrator that designs versions, implements features via Claude Code CLI, runs quality gates, and manages the full PR lifecycle.

## Features Documented: 12

1. Video Library Management (scan, metadata, thumbnails, FTS5 search)
2. Project Management (create, clips with in/out points, update/delete, timeline ordering)
3. Effect Application (9 effects, full CRUD lifecycle, JSON Schema validation)
4. Transition Application (adjacent clip transitions, 59 types, validation)
5. Effect Discovery (schemas, AI hints, live filter preview)
6. Effect Workshop GUI (catalog, parameter forms, filter preview, effect stack)
7. Filesystem Browser (directory browsing with security validation)
8. Web Dashboard (health cards, metrics, WebSocket activity log)
9. Async Job Processing (background scanning, progress reporting, cancellation)
10. Health Monitoring (liveness/readiness probes)
11. Observability (Prometheus metrics, structured logging, audit trail)
12. Automated Development (auto-dev-mcp version/theme/feature lifecycle)

## User Journeys Created: 4

1. **Editor: Import Videos and Build a Project with Effects** (10 steps, verified against route definitions in `src/stoat_ferret/api/routers/`)
2. **AI Agent: Discover Effects and Drive an Editing Workflow** (8 steps, verified against effects.py and projects.py routers)
3. **Developer: Quality Verification and Deployment** (6 steps, verified against AGENTS.md commands and CI workflow)
4. **Automated Development: auto-dev-mcp Feature Delivery** (6 steps, verified against comms/ structure and PLAN.md)

All journey steps were verified against actual route definitions (`@router.get/post/patch/delete` decorators in routers/), handler implementations, and test assertions. Rendering to output file is qualified as "not yet implemented" since no render/export endpoint exists.

## External Dependencies: 6

1. **FFmpeg / ffprobe** (Required) -- Video metadata extraction and thumbnail generation via subprocess
2. **Local Filesystem** (Required) -- Source videos, SQLite database, thumbnails
3. **SQLite** (Required) -- Embedded database via aiosqlite with Alembic migrations
4. **Prometheus** (Optional) -- Metrics collection via HTTP `/metrics` endpoint
5. **GitHub Actions CI** (Optional) -- 9-matrix automated testing (3 OS x 3 Python)
6. **Docker** (Optional) -- Multi-stage containerized deployment

## Sources Used

- `docs/C4-Documentation/c4-container.md` -- Container diagram and interfaces
- `docs/C4-Documentation/c4-component.md` -- Component overview and relationships
- `docs/C4-Documentation/c4-context.md` -- Existing context document (delta mode base)
- `README.md` -- Project description
- `docs/auto-dev/PLAN.md` -- Development plan with version history
- `AGENTS.md` -- Project structure, commands, coding standards
- `src/stoat_ferret/api/routers/*.py` -- Route definitions (8 router files)
- `src/stoat_ferret/api/settings.py` -- Application configuration
- `tests/**/*.py` -- 908 test functions across 56 test files
- `gui/e2e/*.spec.ts` -- 6 Playwright E2E test suites
- `.github/workflows/ci.yml` -- CI configuration

## Key Changes from Previous Version

- Added **auto-dev-mcp** as a fourth persona (programmatic development orchestrator)
- Added **Filesystem Browser** and **Automated Development** as system features
- Added **Automated Development** user journey (auto-dev-mcp feature delivery lifecycle)
- Qualified rendering status: explicitly noted that video rendering to output files is not yet implemented
- Qualified deployment status: noted system is not published to any package registry
- Updated long description to reflect v011 state and alpha status
