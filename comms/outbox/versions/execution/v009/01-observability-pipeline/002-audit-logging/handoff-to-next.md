# Handoff: 002-audit-logging

## What Was Done

- `AuditLogger` is now wired into the DI chain via a separate sync `sqlite3.Connection`
- Only `AsyncSQLiteVideoRepository` currently accepts `audit_logger` - project and clip repositories do not yet have audit support
- WAL mode is enabled on the sync connection to prevent blocking the async event loop

## Context for Next Feature

- The sync connection is a local variable in `lifespan()`, closed explicitly during shutdown
- `app.state.audit_logger` is available for any future middleware or route that needs audit access
- ResourceWarnings in tests about unclosed connections are from pydantic internals during GC, not from our code
