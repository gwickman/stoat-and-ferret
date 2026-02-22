# v009 Version Design

## Overview

**Version:** v009
**Title:** Complete the observability pipeline (FFmpeg metrics, audit logging, file-based logs) and fix GUI runtime gaps (SPA routing, pagination, WebSocket broadcasts).
**Themes:** 2

## Backlog Items

- [BL-057](docs/auto-dev/BACKLOG.md#bl-057)
- [BL-059](docs/auto-dev/BACKLOG.md#bl-059)
- [BL-060](docs/auto-dev/BACKLOG.md#bl-060)
- [BL-063](docs/auto-dev/BACKLOG.md#bl-063)
- [BL-064](docs/auto-dev/BACKLOG.md#bl-064)
- [BL-065](docs/auto-dev/BACKLOG.md#bl-065)

## Design Context

### Rationale

All 6 items are wiring gaps — existing components and infrastructure built in earlier versions but never connected. No new functionality is being built.

### Constraints

- BL-057 depends on BL-056 (structured logging, completed in v008)
- Theme 1 modifies app.py startup/DI; Theme 2 modifies API routers — sequential to avoid conflicts
- SPA fallback route must be conditional on gui/dist/ directory existing (LRN-020)
- AuditLogger requires a separate sync sqlite3.Connection (aiosqlite has no public sync access)

### Assumptions

- All referenced classes and infrastructure exist with expected interfaces (verified in Task 004)
- Frontend already handles WebSocket events correctly (ActivityLog parses event payloads)
- The create_app() DI pattern handles test double injection without wrapping (verified in Task 006)

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-observability-pipeline | Wire the three observability components that exist as dead code into the application's DI chain and startup sequence. | 3 |
| 2 | 02-gui-runtime-fixes | Fix three runtime gaps in the GUI and API layer: SPA routing, pagination totals, and WebSocket broadcasts. | 3 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (observability-pipeline): Wire the three observability components that exist as dead code into the application's DI chain and startup sequence.
- [ ] Theme 02 (gui-runtime-fixes): Fix three runtime gaps in the GUI and API layer: SPA routing, pagination totals, and WebSocket broadcasts.
