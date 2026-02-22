## Context

When wiring components that require synchronous database access (e.g., audit loggers) into an application that uses asynchronous database connections (aiosqlite), you need concurrent access to the same database from both sync and async code paths.

## Learning

Open a separate synchronous `sqlite3.Connection` alongside the async `aiosqlite` connection to the same database file, with WAL (Write-Ahead Logging) mode enabled on both. WAL mode allows concurrent reads and writes from multiple connections without deadlocks.

## Evidence

In v009, `AuditLogger` required synchronous `sqlite3` access while the app used `aiosqlite`. A separate sync connection with WAL mode was opened in the lifespan function. Concurrent tests confirmed no deadlocks occur. The sync connection is closed before the async connection during shutdown to maintain proper ordering.

## Application

When adding components that need synchronous database access to an async application:
1. Open a separate sync connection with `sqlite3.connect()`
2. Enable WAL mode: `conn.execute("PRAGMA journal_mode=WAL")`
3. Close sync connection before async connection during shutdown
4. Use concurrent tests to verify no deadlocks under load