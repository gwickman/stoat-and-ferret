# Version Context — v009

## Version Goals

**v009 — Observability & GUI Runtime**

Complete the observability pipeline (FFmpeg metrics, audit logging, file-based logs) and fix GUI runtime gaps (SPA routing, pagination, WebSocket broadcasts).

## Themes and Features

### Theme 1: observability-pipeline

| Feature | Description | Backlog |
|---------|-------------|---------|
| 001-ffmpeg-observability | Wire `ObservableFFmpegExecutor` into DI chain | BL-059 (P1) |
| 002-audit-logging | Wire `AuditLogger` into repository DI | BL-060 (P2) |
| 003-file-logging | Add `RotatingFileHandler` to `configure_logging()` | BL-057 (P2) |

### Theme 2: gui-runtime-fixes

| Feature | Description | Backlog |
|---------|-------------|---------|
| 001-spa-routing | Add SPA fallback to serve index.html for GUI sub-paths | BL-063 (P1) |
| 002-pagination-fix | Add `count()` to `AsyncProjectRepository`, fix total in GET /projects | BL-064 (P2) |
| 003-websocket-broadcasts | Wire `ConnectionManager.broadcast()` calls into API operations | BL-065 (P2) |

## Referenced Backlog Items

IDs for Task 002 detailed retrieval:
- BL-057 (P2) — File logging
- BL-059 (P1) — FFmpeg observability
- BL-060 (P2) — Audit logging
- BL-063 (P1) — SPA routing
- BL-064 (P2) — Pagination fix
- BL-065 (P2) — WebSocket broadcasts

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| BL-056 (structured logging wired) | Completed (v008) | BL-057 depends on this |
| All other BL items | Independent | No inter-feature dependencies within v009 |

## Constraints and Assumptions

- BL-065 (WebSocket broadcasts) is flagged as higher risk because it touches multiple API endpoints
- No investigation dependencies required — all items are implementation-ready
- No external dependencies or blocked items

## Deferred Items to Be Aware Of

From previous versions relevant to v009:
- **SPA fallback routing** was deferred from v005 — now addressed by BL-063
- **WebSocket connection consolidation** was deferred from v005 — partially addressed by BL-065
- **Phase 3: Composition Engine** deferred to post-v010 (not relevant to v009)
- **Drop-frame timecode** deferred to TBD (not relevant to v009)

## Prior Version Context

v008 (immediate predecessor) completed:
- Database schema creation wired into lifespan startup
- Structured logging wired with `settings.log_level`
- Orphaned settings wired to consumers (all 9 Settings fields now consumed)
- Flaky E2E assertion fixed

These provide the foundation that v009 builds upon, particularly BL-057 (file logging) which depends on the structured logging infrastructure from v008.
