# v009 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: observability-pipeline

**Path:** `comms/inbox/versions/execution/v009/01-observability-pipeline/`
**Goal:** Wire the three observability components that exist as dead code into the application's DI chain and startup sequence. After this theme, FFmpeg operations emit metrics and structured logs, database mutations produce audit entries, and all logs are persisted to rotating files.

**Features:**

- 001-ffmpeg-observability: Wire ObservableFFmpegExecutor into DI so FFmpeg operations emit metrics and structured logs.
- 002-audit-logging: Wire AuditLogger into repository DI with a separate sync connection so database mutations produce audit entries.
- 003-file-logging: Add RotatingFileHandler to configure_logging() for persistent log output to rotating files.
### Theme 02: gui-runtime-fixes

**Path:** `comms/inbox/versions/execution/v009/02-gui-runtime-fixes/`
**Goal:** Fix three runtime gaps in the GUI and API layer: SPA routing fallback for direct navigation, correct pagination totals for the projects endpoint, and WebSocket broadcast calls for real-time event delivery to the frontend.

**Features:**

- 001-spa-routing: Replace StaticFiles mount with catch-all route that serves both static files and SPA fallback.
- 002-pagination-fix: Add count() to AsyncProjectRepository, fix total in API, and add frontend pagination UI.
- 003-websocket-broadcasts: Wire broadcast() into scan service and project router for real-time WebSocket events.
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
