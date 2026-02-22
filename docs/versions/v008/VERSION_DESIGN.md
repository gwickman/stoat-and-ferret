# v008 Version Design

## Overview

**Version:** v008
**Title:** Fix P0 blockers and critical startup wiring gaps so a fresh install starts cleanly with working logging, database, and settings.
**Themes:** 2

## Backlog Items

- [BL-055](docs/auto-dev/BACKLOG.md#bl-055)
- [BL-056](docs/auto-dev/BACKLOG.md#bl-056)
- [BL-058](docs/auto-dev/BACKLOG.md#bl-058)
- [BL-062](docs/auto-dev/BACKLOG.md#bl-062)

## Design Context

### Rationale

v008 addresses the most critical wiring gaps discovered by the post-v007 wiring audit. Database schema creation, structured logging, and orphaned settings were all built in earlier versions but never connected to the application startup sequence. The flaky E2E test blocks CI reliability for all future development.

### Constraints

- All changes are wiring of existing infrastructure — no new feature development
- Theme 1 features must execute sequentially due to shared modification point (app.py)
- BL-055 AC #1 (10 consecutive CI runs) is a post-merge validation criterion

### Assumptions

- CREATE TABLE IF NOT EXISTS is sufficient for v008 (no schema migrations needed)
- configure_logging() idempotency fix prevents handler accumulation in tests
- uvicorn accepts all Python standard logging level names in lowercase

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-application-startup-wiring | Wire existing but disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence. | 3 |
| 2 | 02-ci-stability | Eliminate the flaky E2E test that intermittently blocks CI merges. | 1 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (application-startup-wiring): Wire existing but disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence.
- [ ] Theme 02 (ci-stability): Eliminate the flaky E2E test that intermittently blocks CI merges.
