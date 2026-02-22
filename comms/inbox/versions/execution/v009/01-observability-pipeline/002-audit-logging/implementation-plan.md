# Implementation Plan: audit-logging

## Overview

Wire `AuditLogger` into the repository dependency injection chain by opening a separate synchronous SQLite connection in the lifespan function, instantiating AuditLogger, and passing it to repository constructors. Add `audit_logger` as a `create_app()` kwarg for test injection.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/app.py` | Modify | Add `audit_logger` kwarg to `create_app()`, create sync connection and AuditLogger in lifespan, pass to repos |
| `tests/test_api/conftest.py` | Modify | Update test fixtures if needed for `audit_logger` kwarg |
| `tests/test_api/test_di_wiring.py` | Modify | Add test verifying `audit_logger` stored on `app.state` |
| `tests/test_audit_logging.py` | Modify | Add tests for audit logger wiring, entry creation, and sync connection lifecycle |

## Test Files

`tests/test_api/test_di_wiring.py tests/test_audit_logging.py`

## Implementation Stages

### Stage 1: Add sync connection and AuditLogger to lifespan

1. Add `audit_logger: AuditLogger | None = None` kwarg to `create_app()`
2. In lifespan (when not `_deps_injected`):
   - After creating the aiosqlite connection, open a separate `sqlite3.Connection` to the same database file
   - Create `AuditLogger(conn=sync_conn)`
   - Store on `app.state.audit_logger`
3. Pass `audit_logger` to repository constructors that accept it (e.g., `AsyncSQLiteVideoRepository`)
4. During lifespan cleanup: close the sync connection before closing aiosqlite
5. When `audit_logger` kwarg is provided: store directly on `app.state.audit_logger`

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_api/test_di_wiring.py -x
```

### Stage 2: Add tests

1. Test that `app.state.audit_logger` is an AuditLogger instance after startup
2. Test that `create_app(audit_logger=mock)` stores mock directly
3. Test that separate sync connection is created and closed during lifespan
4. Test that database mutations produce audit log entries with correct fields
5. Test that audit entries are written while async operations continue (no deadlock)

**Verification:**
```bash
uv run pytest tests/test_audit_logging.py tests/test_api/test_di_wiring.py -x
```

## Test Infrastructure Updates

- Existing tests using `create_app()` should continue working since `audit_logger` defaults to `None`
- Tests creating repositories directly will not have audit logging (expected behavior)

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Sync connection blocking the event loop — mitigated by lightweight single INSERT per mutation. See `006-critical-thinking/risk-assessment.md`.
- Connection lifecycle management — sync connection must close before aiosqlite to avoid database locks.

## Commit Message

```
feat(observability): wire AuditLogger into repository DI chain

BL-060: Create separate sync sqlite3.Connection for AuditLogger in lifespan.
Pass audit_logger to repository constructors so database mutations produce
audit entries. Add audit_logger kwarg to create_app() for test injection.
```