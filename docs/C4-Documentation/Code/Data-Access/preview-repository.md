# Preview Repository

**Source:** `src/stoat_ferret/db/preview_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for preview session persistence. Defines AsyncPreviewRepository protocol and offers two implementations: SQLitePreviewRepository for production use and InMemoryPreviewRepository for testing. Handles HLS preview session CRUD operations with strict status transition validation and TTL-based expiry tracking.

## Public Interface

### Protocols

- `AsyncPreviewRepository`
  - Abstract protocol defining asynchronous preview session repository operations
  - Methods:
    - `async add(session: PreviewSession) -> PreviewSession` — Add a new preview session record
    - `async get(session_id: str) -> PreviewSession | None` — Get a preview session by ID
    - `async list_by_project(project_id: str) -> list[PreviewSession]` — List all preview sessions for a project
    - `async update(session: PreviewSession) -> None` — Update a preview session with transition validation
    - `async delete(session_id: str) -> bool` — Delete a preview session record
    - `async get_expired(now: datetime | None = None) -> list[PreviewSession]` — Get sessions where expires_at < now
    - `async count() -> int` — Count all preview session records

### Classes

- `SQLitePreviewRepository`
  - Async SQLite implementation of AsyncPreviewRepository protocol
  - `__init__(conn: aiosqlite.Connection) -> None`
    - Initialize with async SQLite connection
    - Sets row_factory to aiosqlite.Row for named column access
  - `async add(session: PreviewSession) -> PreviewSession` — INSERT into preview_sessions table
    - Serializes PreviewStatus and PreviewQuality enums to string values
    - Serializes all datetime fields to ISO format strings
    - Raises ValueError if session with same ID already exists (IntegrityError wrapper)
  - `async get(session_id: str) -> PreviewSession | None` — SELECT by id
  - `async list_by_project(project_id: str) -> list[PreviewSession]` — SELECT by project_id
    - Returns sessions ordered by created_at (ascending)
  - `async update(session: PreviewSession) -> None` — UPDATE preview session
    - Validates status transition if status changed
    - Raises ValueError if session not found (rowcount == 0) or transition invalid
    - Updates manifest_path, segment_count, expires_at, error_message
  - `async delete(session_id: str) -> bool` — DELETE by id
    - Returns True if deleted, False if not found
  - `async get_expired(now: datetime | None = None) -> list[PreviewSession]` — SELECT sessions where expires_at < now
    - Defaults to current UTC time if now is None
    - Returns sessions ordered by expires_at (ascending) for cleanup operations
  - `async count() -> int` — SELECT COUNT(*) FROM preview_sessions
  - `_row_to_session(row: aiosqlite.Row) -> PreviewSession` — Convert database row to PreviewSession
    - Deserializes enum values back from strings
    - Converts ISO format strings back to datetime objects

- `InMemoryPreviewRepository`
  - In-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains index: `_sessions` (session_id → PreviewSession)
  - `__init__() -> None` — Initialize empty repository
  - `async add(session: PreviewSession) -> PreviewSession` — Store deepcopy in _sessions
    - Raises ValueError if session with same ID already exists
    - Returns deepcopy to prevent external mutations
  - `async get(session_id: str) -> PreviewSession | None` — Return deepcopy from _sessions
  - `async list_by_project(project_id: str) -> list[PreviewSession]` — Return deepcopies matching project_id
    - Sorted by created_at (ascending)
  - `async update(session: PreviewSession) -> None` — Update _sessions entry
    - Validates status transition if status changed
    - Raises ValueError if session not found or transition invalid
  - `async delete(session_id: str) -> bool` — Remove from _sessions
    - Returns True if deleted, False if not found
  - `async get_expired(now: datetime | None = None) -> list[PreviewSession]` — Return deepcopies where expires_at < now
    - Defaults to current UTC time if now is None
    - Sorted by expires_at (ascending)
  - `async count() -> int` — Return len(self._sessions)

## Dependencies

- **stoat_ferret.db.models**: PreviewSession, PreviewStatus, PreviewQuality, validate_preview_transition
- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection and aiosqlite.Row
- **datetime**: For timestamp fields and expiry checking
- **copy**: For deepcopy isolation in in-memory repository
- **typing**: For Protocol and runtime_checkable
- **structlog**: For logging preview repository operations

## Key Implementation Details

### Status Transitions

Valid transitions are enforced via `validate_preview_transition()` from models:
```
initializing -> generating, error, expired
generating -> ready, error, expired
ready -> seeking, error, expired
seeking -> ready, error, expired
error -> expired
expired -> (terminal, no transitions)
```

Terminal states (error, expired) can only transition to expired or remain terminal.

### Enum Serialization

- **PreviewStatus**: Stored as string in database (e.g., "ready")
  - Deserialized back to enum on retrieval via PreviewStatus(value)
- **PreviewQuality**: Stored as string in database (e.g., "high")
  - Deserialized back to enum on retrieval via PreviewQuality(value)

### TTL and Expiry

- Each session has `expires_at` datetime field for time-to-live management
- `get_expired()` queries sessions where expires_at < now for cleanup operations
- Useful for the cleanup service to find and remove expired preview sessions
- Defaults to current UTC time if no time provided

### Manifest Path and Segment Count

- `manifest_path` is NULL until preview is ready (generation complete)
- `segment_count` is 0 until generation completes, then tracks number of HLS segments
- Both are updated when session transitions to "ready" status

### Error Tracking

- `error_message` is NULL for successful operations
- Contains descriptive error text when status is "error"
- Cleared (set to NULL) if session recovers from error state

### Deepcopy Isolation

- InMemoryPreviewRepository stores and returns deepcopies to prevent test code from accidentally mutating internal state
- Each returned record is independent and changes won't affect future queries

### Pagination and Counting

- `list_by_project()` returns all sessions for a project (no pagination)
- `count()` returns total number of all sessions
- `get_expired()` used for batch expiry cleanup rather than paginated queries

## Relationships

- **Used by:**
  - Preview generation service for session lifecycle management
  - HLS endpoint handlers for manifest serving
  - Cleanup job for removing expired preview sessions
  - API endpoints for preview status queries

- **Uses:**
  - models.PreviewSession — the primary data model
  - models.validate_preview_transition — status validation
  - aiosqlite — async database operations
  - datetime — timestamp management

- **Associated entities:**
  - Projects (via project_id FK) — each preview session generates HLS for a project
  - Videos (indirectly through projects) — source content for preview generation
