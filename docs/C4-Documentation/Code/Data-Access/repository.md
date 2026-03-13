# Repository

**Source:** `src/stoat_ferret/db/repository.py`
**Component:** Data Access

## Purpose

Provides synchronous repository pattern implementations for video metadata storage. Defines the VideoRepository protocol and offers two implementations: SQLiteVideoRepository for production use and InMemoryVideoRepository for testing. Implements CRUD operations and FTS5 full-text search functionality.

## Public Interface

### Protocols

- `VideoRepository`
  - Abstract protocol defining synchronous video repository operations
  - Methods:
    - `add(video: Video) -> Video` — Add a new video, raises ValueError if duplicate ID or path
    - `get(id: str) -> Video | None` — Get video by ID
    - `get_by_path(path: str) -> Video | None` — Get video by file path
    - `list_videos(limit: int = 100, offset: int = 0) -> list[Video]` — Paginated list ordered by creation date descending
    - `search(query: str, limit: int = 100) -> list[Video]` — Full-text search by filename or path
    - `update(video: Video) -> Video` — Update existing video, raises ValueError if not found
    - `delete(id: str) -> bool` — Delete video by ID, returns True if deleted

### Classes

- `SQLiteVideoRepository`
  - SQLite implementation of VideoRepository protocol
  - `__init__(conn: sqlite3.Connection, audit_logger: AuditLogger | None = None) -> None`
    - Initialize with SQLite connection and optional audit logger
  - `add(video: Video) -> Video` — INSERT into videos table
  - `get(id: str) -> Video | None` — SELECT by id
  - `get_by_path(path: str) -> Video | None` — SELECT by path
  - `list_videos(limit: int = 100, offset: int = 0) -> list[Video]` — SELECT with pagination, ordered by created_at DESC
  - `search(query: str, limit: int = 100) -> list[Video]` — Uses FTS5 MATCH with prefix search (wraps query in quotes with asterisk: `"query"*`)
  - `update(video: Video) -> Video` — UPDATE all fields, computes diff if audit logger present
  - `delete(id: str) -> bool` — DELETE by id
  - `_row_to_video(row: sqlite3.Row) -> Video` — Convert database row to Video object
  - `_compute_diff(old: Video, new: Video) -> dict[str, object]` — Compute field-level changes for audit logging

- `InMemoryVideoRepository`
  - In-memory test implementation of VideoRepository protocol
  - Maintains two indices: `_videos` (id → Video) and `_by_path` (path → id)
  - `__init__() -> None` — Initialize empty repository
  - `add(video: Video) -> Video` — Store in _videos and _by_path
  - `get(id: str) -> Video | None` — Retrieve from _videos
  - `get_by_path(path: str) -> Video | None` — Lookup id in _by_path, then retrieve
  - `list_videos(limit: int = 100, offset: int = 0) -> list[Video]` — Return paginated list sorted by created_at DESC
  - `search(query: str, limit: int = 100) -> list[Video]` — Per-token prefix matching approximating FTS5 behavior
  - `update(video: Video) -> Video` — Update _videos entry, refresh _by_path if path changed
  - `delete(id: str) -> bool` — Remove from both indices

### Helper Functions

- `_any_token_startswith(text: str, prefix: str) -> bool`
  - Tokenizes text by splitting on non-alphanumeric characters
  - Checks if any token starts with prefix (case-insensitive comparison)
  - Used by InMemoryVideoRepository.search() to approximate FTS5 matching

## Dependencies

- **stoat_ferret.db.models**: Video dataclass
- **stoat_ferret.db.audit** (TYPE_CHECKING): AuditLogger for change tracking
- **sqlite3**: Python standard library for database connection and Row type
- **datetime**: For Video timestamp fields
- **re**: Regular expression module for tokenization in _any_token_startswith()

## Key Implementation Details

### FTS5 Search

- SQLiteVideoRepository uses FTS5 MATCH operator with prefix query pattern: `"query"*`
- Query is quoted and suffixed with asterisk for prefix matching
- Joins videos table with videos_fts virtual table
- InMemoryVideoRepository approximates this with per-token prefix matching but is not exact

### Audit Logging

- SQLiteVideoRepository optionally tracks changes via AuditLogger
- add() logs "INSERT" operations
- update() computes diff of changed fields and logs "UPDATE" with changes dict
- delete() logs "DELETE" operations
- Audit logger is optional (None) for cases where change tracking isn't needed

### Synchronous vs Async

- This module provides synchronous operations only
- For async operations, use async_repository.py with AsyncVideoRepository

### Row Conversion

- Uses sqlite3.Row with row_factory = sqlite3.Row for named column access
- Converts ISO format strings back to datetime objects on retrieval
- Handles nullable fields (audio_codec, thumbnail_path)

### In-Memory Implementation

- Uses deepcopy or direct reference depending on caller intent
- Maintains consistency with SQLite version including pagination and sorting order
- Provides deterministic test behavior without database overhead

## Relationships

- **Used by:**
  - Application initialization code (factory functions) to inject VideoRepository dependency
  - Service layer for video metadata operations
  - API route handlers for video endpoints

- **Uses:**
  - models.Video — the primary data model
  - audit.AuditLogger — optional change tracking
  - schema (indirectly) — depends on schema definitions for table structure
