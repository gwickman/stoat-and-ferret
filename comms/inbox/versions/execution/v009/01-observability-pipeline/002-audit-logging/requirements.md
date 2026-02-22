# Requirements: audit-logging

## Goal

Wire AuditLogger into repository dependency injection with a separate sync connection so database mutations produce audit entries.

## Background

Backlog Item: BL-060

`AuditLogger` was built in v002/03-database-foundation and repository constructors accept it as a parameter, but it is never instantiated — the parameter is always None. No audit trail is produced for any database operation. This feature connects the existing component using a separate synchronous SQLite connection.

## Functional Requirements

**FR-001: Separate sync connection**
- Open a `sqlite3.Connection` to the same database file in the lifespan function, separate from the aiosqlite connection
- Pass this sync connection to `AuditLogger(conn=sync_conn)`
- Close the sync connection during lifespan cleanup (before closing aiosqlite)
- Acceptance: A separate `sqlite3.Connection` exists during application runtime for audit logging

**FR-002: AuditLogger DI wiring**
- Instantiate AuditLogger with the sync connection and store on `app.state`
- Pass audit_logger to repository constructors that accept it
- Acceptance: `app.state.audit_logger` is an AuditLogger instance after startup

**FR-003: create_app() kwarg support**
- Add `audit_logger` kwarg to `create_app()` following the existing DI pattern
- When provided, skip lifespan audit logger creation (via `_deps_injected` flag)
- Acceptance: `create_app(audit_logger=mock)` stores `mock` on `app.state.audit_logger`

**FR-004: Audit entry creation**
- Database mutations (create, update, delete) produce audit log entries
- Entries include correlation ID, resource type, and operation type
- Acceptance: After a CRUD operation, the audit_log table contains a matching entry

## Non-Functional Requirements

**NFR-001: No deadlock under concurrent operations**
- Audit INSERT on the sync connection must not block async operations on the aiosqlite connection
- Metric: Concurrent async operations complete without timeout while audit entries are written

## Out of Scope

- Modifying `AuditLogger` class internals
- Adding new audit event types beyond what AuditLogger already supports
- Async AuditLogger implementation (documented as future improvement)
- Audit log querying or visualization

## Test Requirements

- Unit: Verify AuditLogger is instantiated and injected into repositories (AC1)
- Unit: Verify `create_app(audit_logger=...)` stores logger on `app.state`
- Unit: Verify separate sync `sqlite3.Connection` is created and closed during lifespan
- Integration: Verify database mutations produce audit log entries (AC2)
- Integration: Verify audit entries include correlation ID, resource type, and operation type (AC3)
- Integration: Verify audit entries are written while async operations continue (no deadlock)
- Existing: `tests/test_api/conftest.py` may need update for `audit_logger` kwarg

See `comms/outbox/versions/design/v009/005-logical-design/test-strategy.md` for full test strategy.

## Reference

See `comms/outbox/versions/design/v009/004-research/` for supporting evidence.