# Clip Repository

## Goal
Create async repository for clip persistence.

## Requirements

### FR-001: AsyncClipRepository Protocol
Define protocol with:
- add(clip) -> Clip
- get(id) -> Clip | None
- list_by_project(project_id) -> list[Clip]
- update(clip) -> Clip
- delete(id) -> bool

### FR-002: Implementation
AsyncSQLiteClipRepository using aiosqlite.

### FR-003: InMemory Implementation
AsyncInMemoryClipRepository for testing.

### FR-004: Contract Tests
Parametrized tests for async implementations.

## Acceptance Criteria
- [ ] Protocol defined
- [ ] SQLite implementation complete
- [ ] In-memory implementation complete
- [ ] Contract tests pass