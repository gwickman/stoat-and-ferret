# Theme 03: library-api

## Overview

Implement REST endpoints for video library management with full query capabilities. All endpoints use the async repository from Theme 1.

## Context

Roadmap milestone M1.6 specifies:
- `/videos` endpoints with structured error responses
- `/scan` endpoint with progress reporting
- `/search` endpoint with FTS5 full-text search

API specification document: `docs/design/05-api-specification.md`

Explorations completed:
- `fastapi-testing-patterns`: TestClient and dependency override patterns
- `aiosqlite-migration`: Async repository patterns

## Architecture Decisions

### AD-001: Dependency Injection for Repository
Use FastAPI Depends for repository:
```python
async def get_repository(request: Request) -> AsyncVideoRepository:
    return AsyncSQLiteVideoRepository(request.app.state.db)
```

### AD-002: Pydantic Models for Request/Response
Define schemas in `src/stoat_ferret/api/schemas/`.

### AD-003: Synchronous Scan
Scan executes synchronously (blocks until complete). Job queue deferred to v004.

## Dependencies
- Theme 2 complete (FastAPI app, middleware)
- Theme 1 Feature 1 (async-repository)

## Execution Order
Sequential: 1 → 2 → 3 → 4

## Evidence Sources

| Claim | Source |
|-------|--------|
| TestClient usage pattern | `comms/outbox/exploration/fastapi-testing-patterns/testclient-usage.md` |
| dependency_overrides pattern | `comms/outbox/exploration/fastapi-testing-patterns/dependency-injection.md` |
| Shared conftest fixtures | `comms/outbox/exploration/fastapi-testing-patterns/conftest-additions.md` |
| AsyncSQLiteVideoRepository usage | `comms/outbox/exploration/aiosqlite-migration/async-repository-pattern.md` |

## Success Criteria
- All endpoints match API specification
- 100% test coverage for endpoints
- Error responses follow standard format