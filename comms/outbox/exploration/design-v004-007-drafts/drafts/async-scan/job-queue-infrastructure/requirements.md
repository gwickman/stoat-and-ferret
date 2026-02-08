# Requirements — job-queue-infrastructure

## Goal

Create AsyncJobQueue protocol, asyncio.Queue implementation, and lifespan integration.

## Background

The scan endpoint blocks the HTTP request until the entire directory scan completes (`src/stoat_ferret/api/services/scan.py:16`). No job queue concept exists in the codebase. The `asyncio.Queue` producer-consumer pattern was selected over external dependencies (Redis, arq) per external research. `InMemoryJobQueue` was created in BL-020 (Theme 01) for test use; this feature creates the production async implementation.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | `AsyncJobQueue` protocol defines `submit()`, `get_status()`, `get_result()` methods | BL-027 |
| FR-2 | `AsyncioJobQueue` implements the protocol using `asyncio.Queue` producer-consumer pattern | BL-027 |
| FR-3 | Job worker starts on application startup via lifespan context manager | BL-027 |
| FR-4 | Job worker cancels gracefully on application shutdown | BL-027 |
| FR-5 | Default 5-minute timeout per job, configurable | BL-027 |
| FR-6 | Jobs track status: pending, running, completed, failed | BL-027 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | `InMemoryJobQueue` (from BL-020) and `AsyncioJobQueue` both satisfy the `AsyncJobQueue` protocol |
| NFR-2 | Job queue integrated into `create_app()` DI pattern (from BL-021) |
| NFR-3 | Worker process logs job lifecycle events |

## Out of Scope

- External job queue backends (Redis, Celery, arq)
- Multiple worker processes — single worker sufficient for current scale
- Job persistence across application restarts
- Job priority or scheduling

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Unit | AsyncioJobQueue: submit, poll status, completion, failure, timeout | 5–8 |
| Unit | InMemoryJobQueue: synchronous execution, deterministic results | 3–5 |
| Unit | Lifespan integration: worker starts on startup, cancels on shutdown | 2–3 |
