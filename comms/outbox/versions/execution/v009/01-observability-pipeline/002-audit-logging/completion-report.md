---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-audit-logging

## Summary

Wired AuditLogger into the repository dependency injection chain. A separate synchronous `sqlite3.Connection` is opened in the lifespan function alongside the existing aiosqlite connection, used to instantiate `AuditLogger`, and passed to `AsyncSQLiteVideoRepository`. Added `audit_logger` kwarg to `create_app()` following the existing DI pattern.

## Acceptance Criteria

- **FR-001: Separate sync connection** - PASS. A `sqlite3.Connection` is opened to the same database file in lifespan, with WAL mode enabled for concurrent access. Closed before aiosqlite during shutdown.
- **FR-002: AuditLogger DI wiring** - PASS. `AuditLogger` is instantiated with the sync connection and stored on `app.state.audit_logger`. Passed to `AsyncSQLiteVideoRepository` constructor.
- **FR-003: create_app() kwarg support** - PASS. `audit_logger` kwarg added to `create_app()`. When provided, stored directly on `app.state.audit_logger`, skipping lifespan creation via `_deps_injected` flag.
- **FR-004: Audit entry creation** - PASS. Database mutations via `AsyncSQLiteVideoRepository.add()` produce audit log entries with operation type, entity type, and entity ID.

## Changes Made

| File | Change |
|------|--------|
| `src/stoat_ferret/api/app.py` | Added `sqlite3` and `AuditLogger` imports; created sync connection with WAL mode in lifespan; instantiated `AuditLogger` and stored on `app.state`; passed `audit_logger` to `AsyncSQLiteVideoRepository`; close sync connection before aiosqlite on shutdown; added `audit_logger` kwarg to `create_app()` |
| `tests/test_api/test_di_wiring.py` | Added `test_create_app_with_audit_logger_stores_on_state` test |
| `tests/test_audit_logging.py` | Added `TestAsyncRepositoryAuditWiring` class (async repo audit entry creation, no-deadlock concurrent test) and `TestLifespanAuditWiring` class (lifespan creates audit logger, sync connection closed after shutdown) |

## Test Results

- 901 passed, 20 skipped, 0 failed
- Coverage: 92.85% (threshold: 80%)
- `app.py` coverage: 100%

## Quality Gates

- ruff check: pass
- ruff format: pass
- mypy: pass (0 issues in 49 source files)
- pytest: pass (901 passed)
