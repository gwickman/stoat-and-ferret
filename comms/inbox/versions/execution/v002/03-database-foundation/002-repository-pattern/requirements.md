# Repository Pattern

## Goal
Create VideoRepository protocol with SQLite and InMemory implementations.

## Requirements

### FR-001: Video Dataclass
Create Video dataclass matching schema:
- All fields from videos table
- frame_rate property computing float from num/den

### FR-002: VideoRepository Protocol
Define protocol with methods:
- add(video: Video) -> Video
- get(id: str) -> Video | None
- get_by_path(path: str) -> Video | None
- list(limit: int, offset: int) -> list[Video]
- search(query: str, limit: int) -> list[Video]
- update(video: Video) -> Video
- delete(id: str) -> bool

### FR-003: SQLiteVideoRepository
Implement protocol using sqlite3 connection.

### FR-004: InMemoryVideoRepository
Implement protocol using dict storage.
- For testing without database

### FR-005: Contract Tests
Tests that run against both implementations to verify identical behavior.

## Acceptance Criteria
- [ ] Video dataclass with all fields
- [ ] VideoRepository protocol defined
- [ ] SQLiteVideoRepository passes all contract tests
- [ ] InMemoryVideoRepository passes all contract tests