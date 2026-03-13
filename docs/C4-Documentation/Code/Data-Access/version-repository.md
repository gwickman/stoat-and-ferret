# Version Repository

**Source:** `src/stoat_ferret/db/version_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for project timeline versioning and history management. Defines AsyncVersionRepository protocol and offers two implementations: AsyncSQLiteVersionRepository for production use and AsyncInMemoryVersionRepository for testing. Manages non-destructive version restoration with data integrity validation via SHA-256 checksums.

## Public Interface

### Data Classes

- `VersionRecord`
  - Represents a saved version of a project timeline
  - Properties:
    - `id: int | None` — Database row ID (None for unsaved records)
    - `project_id: str` — The project this version belongs to
    - `version_number: int` — Auto-incremented version number per project (1-based)
    - `timeline_json: str` — Serialized timeline data
    - `checksum: str` — SHA-256 hex digest of timeline_json
    - `created_at: datetime` — When this version was created

### Functions

- `compute_checksum(timeline_json: str) -> str`
  - Computes SHA-256 checksum for timeline JSON data
  - Returns hex digest of the hash
  - Used for data integrity validation

### Protocols

- `AsyncVersionRepository`
  - Abstract protocol defining asynchronous version repository operations
  - Methods:
    - `async save(project_id: str, timeline_json: str) -> VersionRecord` — Save a new version with auto-incremented version number
    - `async list_versions(project_id: str) -> list[VersionRecord]` — List all versions for a project, ordered by version number descending (most recent first)
    - `async get_version(project_id: str, version_number: int) -> VersionRecord | None` — Get a specific version by project and version number
    - `async restore(project_id: str, version_number: int) -> VersionRecord` — Restore a previous version as a new version (non-destructive)

### Classes

- `AsyncSQLiteVersionRepository`
  - Async SQLite implementation of AsyncVersionRepository protocol
  - `__init__(conn: aiosqlite.Connection) -> None`
    - Initialize with async SQLite connection
  - `async save(project_id: str, timeline_json: str) -> VersionRecord` — INSERT new version
    - Auto-computes checksum via compute_checksum()
    - Auto-increments version number via _next_version_number()
    - Uses UTC timestamp for created_at
    - Returns VersionRecord with id from cursor.lastrowid
  - `async list_versions(project_id: str) -> list[VersionRecord]` — SELECT all versions for project, ordered by version_number DESC
  - `async get_version(project_id: str, version_number: int) -> VersionRecord | None` — SELECT by project_id and version_number
  - `async restore(project_id: str, version_number: int) -> VersionRecord` — Non-destructive restore
    - Gets source version, validates checksum
    - Calls save() to create new version with source version's timeline_json
    - Raises ValueError if source version not found or checksum mismatch
  - `async _next_version_number(project_id: str) -> int` — Helper to get next version number
    - Uses MAX(version_number) query
    - Returns 1 for first version, or max + 1 for subsequent
  - `_row_to_record(row: aiosqlite.Row) -> VersionRecord` — Convert database row to VersionRecord

- `AsyncInMemoryVersionRepository`
  - Async in-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains: `_versions` (project_id → list[VersionRecord]) and `_next_id` (int) for row ID generation
  - `__init__() -> None` — Initialize empty storage
  - `async save(project_id: str, timeline_json: str) -> VersionRecord` — Create and store new version
    - Auto-computes checksum
    - Auto-increments version number per project
    - Uses UTC timestamp for created_at
    - Returns the record (not a deepcopy, unlike video repositories)
  - `async list_versions(project_id: str) -> list[VersionRecord]` — Return versions sorted by version_number DESC
  - `async get_version(project_id: str, version_number: int) -> VersionRecord | None` — Retrieve version by number
  - `async restore(project_id: str, version_number: int) -> VersionRecord` — Non-destructive restore
    - Gets source version, validates checksum
    - Calls save() to create new version
    - Raises ValueError if source version not found or checksum mismatch

## Dependencies

- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection and aiosqlite.Row
- **hashlib**: For SHA-256 checksum computation
- **dataclasses**: For VersionRecord dataclass
- **datetime**: For UTC timestamp handling (timezone.utc)
- **copy**: For deepcopy operations in in-memory repository
- **typing**: For type hints (Protocol)

## Key Implementation Details

### Version Numbering

- Each project has its own version sequence starting at 1
- Version numbers are auto-incremented and never reused
- Used to create chronological timeline of edits

### Checksums

- SHA-256 hex digest of timeline_json provides data integrity guarantee
- Restore operation validates checksum of source version before copying
- Prevents restoration of corrupted or tampered version data

### Non-Destructive Restore

- Restore operation creates a new version (doesn't overwrite existing)
- Example: Restoring version 3 when current is 5 creates version 6 with version 3's timeline
- Preserves full edit history for undo/redo workflows
- Allows "restoring" to any previous state while maintaining forward history

### Async/Await Pattern

- All public methods are async and must be awaited
- Uses `await self._conn.execute()`, `await cursor.fetchone()`, `await cursor.fetchall()` for database operations
- Uses `await self._conn.commit()` to persist changes

### Timezone Handling

- Uses datetime.now(timezone.utc) for UTC timestamps
- All created_at values are timezone-aware UTC datetimes
- Ensures consistency across different execution environments

### Deepcopy Isolation

- AsyncInMemoryVersionRepository stores versions in list per project
- Returns deepcopies when listing/getting to prevent external mutations
- Save and restore operations handle copies appropriately

### Database Constraints

- UNIQUE(project_id, version_number) constraint prevents duplicate version numbers per project
- Foreign key on project_id with ON DELETE CASCADE (deleting project removes all versions)
- Composite index on (project_id, version_number) for efficient queries

## Relationships

- **Used by:**
  - FastAPI application lifespan (dependency injection in app.state)
  - Async service layer for timeline versioning operations
  - API route handlers for version history and restore endpoints
  - Tests that need async version repository behavior

- **Uses:**
  - schema (indirectly) — depends on project_versions table schema
  - models.Project — versions are associated with projects
  - hashlib — for checksum computation

- **Associated entities:**
  - project_repository.AsyncSQLiteProjectRepository — versions belong to projects
  - Projects deleted trigger cascade delete of their versions
