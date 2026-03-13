# Async Repository

**Source:** `src/stoat_ferret/db/async_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for video metadata storage, designed for FastAPI and async/await applications. Defines AsyncVideoRepository protocol and offers two implementations: AsyncSQLiteVideoRepository for production use and AsyncInMemoryVideoRepository for testing. All methods are async/await compatible.

## Public Interface

### Protocols

- `AsyncVideoRepository`
  - Abstract protocol defining asynchronous video repository operations
  - Methods:
    - `async add(video: Video) -> Video` — Add a new video, raises ValueError if duplicate ID or path
    - `async get(id: str) -> Video | None` — Get video by ID
    - `async get_by_path(path: str) -> Video | None` — Get video by file path
    - `async list_videos(limit: int = 100, offset: int = 0) -> list[Video]` — Paginated list ordered by creation date descending
    - `async search(query: str, limit: int = 100) -> list[Video]` — Full-text search by filename or path
    - `async update(video: Video) -> Video` — Update existing video, raises ValueError if not found
    - `async count() -> int` — Return total number of videos in repository
    - `async delete(id: str) -> bool` — Delete video by ID, returns True if deleted

### Classes

- `AsyncSQLiteVideoRepository`
  - Async SQLite implementation of AsyncVideoRepository protocol
  - `__init__(conn: aiosqlite.Connection, audit_logger: AuditLogger | None = None) -> None`
    - Initialize with async SQLite connection and optional audit logger
  - `async add(video: Video) -> Video` — INSERT into videos table asynchronously
  - `async get(id: str) -> Video | None` — SELECT by id
  - `async get_by_path(path: str) -> Video | None` — SELECT by path
  - `async list_videos(limit: int = 100, offset: int = 0) -> list[Video]` — SELECT with pagination, ordered by created_at DESC
  - `async search(query: str, limit: int = 100) -> list[Video]` — Uses FTS5 MATCH with prefix search pattern `"query"*`
  - `async count() -> int` — SELECT COUNT(*) FROM videos
  - `async update(video: Video) -> Video` — UPDATE all fields asynchronously
  - `async delete(id: str) -> bool` — DELETE by id
  - `_row_to_video(row: Any) -> Video` — Convert database row to Video object (sync helper)

- `AsyncInMemoryVideoRepository`
  - Async in-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains two indices: `_videos` (id → Video) and `_by_path` (path → id)
  - `__init__() -> None` — Initialize empty repository
  - `async add(video: Video) -> Video` — Store deepcopy in _videos and _by_path
  - `async get(id: str) -> Video | None` — Retrieve deepcopy from _videos
  - `async get_by_path(path: str) -> Video | None` — Lookup id in _by_path, then retrieve deepcopy
  - `async list_videos(limit: int = 100, offset: int = 0) -> list[Video]` — Return paginated deepcopies sorted by created_at DESC
  - `async search(query: str, limit: int = 100) -> list[Video]` — Per-token prefix matching, returns deepcopies
  - `async count() -> int` — Return len(self._videos)
  - `async update(video: Video) -> Video` — Update _videos with deepcopy, refresh _by_path if path changed
  - `async delete(id: str) -> bool` — Remove from both indices
  - `seed(videos: list[Video]) -> None` — Populate repository with initial test data (deepcopies)

### Helper Functions

- `_any_token_startswith(text: str, prefix: str) -> bool`
  - Tokenizes text by splitting on non-alphanumeric characters
  - Checks if any token starts with prefix (case-insensitive comparison)
  - Used by AsyncInMemoryVideoRepository.search() to approximate FTS5 matching

## Dependencies

- **stoat_ferret.db.models**: Video dataclass
- **stoat_ferret.db.audit** (TYPE_CHECKING): AuditLogger for change tracking
- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection
- **sqlite3**: For aiosqlite.IntegrityError and Row type
- **datetime**: For Video timestamp fields
- **re**: Regular expression module for tokenization
- **copy**: For deepcopy isolation in in-memory repository

## Key Implementation Details

### Async/Await Pattern

- All public methods are async and must be awaited
- Uses `await self._conn.execute()`, `await cursor.fetchone()`, `await cursor.fetchall()` for database operations
- Uses `await self._conn.commit()` to persist changes

### FTS5 Search

- AsyncSQLiteVideoRepository uses FTS5 MATCH operator with prefix query pattern: `"query"*`
- Query is quoted and suffixed with asterisk for prefix matching
- Joins videos table with videos_fts virtual table asynchronously
- AsyncInMemoryVideoRepository approximates with per-token prefix matching

### Deepcopy Isolation

- AsyncInMemoryVideoRepository stores and returns deepcopies to prevent external mutations
- Prevents bugs where test code modifies returned objects and affects internal state
- sync helper methods use Any type for row objects (could be aiosqlite.Row or dict)

### Count Operation

- AsyncSQLiteVideoRepository.count() uses SELECT COUNT(*) and asserts result is not None
- AsyncInMemoryVideoRepository.count() returns len(self._videos)
- This operation is critical for FR-002 requirements (project count tracking)

### Audit Logging

- AsyncSQLiteVideoRepository optionally supports AuditLogger (though audit logging not fully async in current implementation)
- add() logs "INSERT" operations
- delete() logs "DELETE" operations
- NOTE: update() does not compute or log diffs in async implementation (unlike sync version)

## Relationships

- **Used by:**
  - FastAPI application lifespan (dependency injection in app.state)
  - Async service layer for video metadata operations
  - API route handlers for video endpoints (async route handlers)
  - Tests that need async repository behavior

- **Uses:**
  - models.Video — the primary data model
  - audit.AuditLogger — optional change tracking
  - schema (indirectly) — depends on schema definitions for table structure
