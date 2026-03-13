# Clip Repository

**Source:** `src/stoat_ferret/db/clip_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for clip metadata storage. Defines AsyncClipRepository protocol and offers two implementations: AsyncSQLiteClipRepository for production use and AsyncInMemoryClipRepository for testing. Handles clip CRUD operations including serialization of JSON fields (effects) and timeline positioning data.

## Public Interface

### Protocols

- `AsyncClipRepository`
  - Abstract protocol defining asynchronous clip repository operations
  - Methods:
    - `async add(clip: Clip) -> Clip` — Add a new clip, raises ValueError if duplicate ID or foreign key violation
    - `async get(id: str) -> Clip | None` — Get clip by ID
    - `async list_by_project(project_id: str) -> list[Clip]` — List clips in a project, ordered by timeline_position
    - `async update(clip: Clip) -> Clip` — Update existing clip, raises ValueError if not found
    - `async delete(id: str) -> bool` — Delete clip by ID, returns True if deleted

### Classes

- `AsyncSQLiteClipRepository`
  - Async SQLite implementation of AsyncClipRepository protocol
  - `__init__(conn: aiosqlite.Connection) -> None`
    - Initialize with async SQLite connection
  - `async add(clip: Clip) -> Clip` — INSERT into clips table
    - Serializes effects to JSON string
    - Supports timeline columns (track_id, timeline_start, timeline_end)
    - Raises ValueError on IntegrityError (duplicate ID or foreign key violation)
  - `async get(id: str) -> Clip | None` — SELECT by id
  - `async list_by_project(project_id: str) -> list[Clip]` — SELECT all clips for project, ordered by timeline_position
  - `async update(clip: Clip) -> Clip` — UPDATE all fields
    - Serializes effects to JSON string
    - Updates timeline columns (track_id, timeline_start, timeline_end)
    - Raises ValueError if clip not found (rowcount == 0)
  - `async delete(id: str) -> bool` — DELETE by id, returns True if deleted
  - `_row_to_clip(row: Any) -> Clip` — Convert database row to Clip object (sync helper)
    - Deserializes JSON effects back to dict
    - Uses dict-style .get() for new timeline columns for backward compatibility with unmigrated databases

- `AsyncInMemoryClipRepository`
  - Async in-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains single index: `_clips` (id → Clip)
  - `__init__() -> None` — Initialize empty storage
  - `async add(clip: Clip) -> Clip` — Store deepcopy in _clips
    - Raises ValueError if clip ID already exists
  - `async get(id: str) -> Clip | None` — Retrieve deepcopy from _clips
  - `async list_by_project(project_id: str) -> list[Clip]` — Return deepcopies filtered by project_id, sorted by timeline_position
  - `async update(clip: Clip) -> Clip` — Update _clips with deepcopy
    - Raises ValueError if clip not found
  - `async delete(id: str) -> bool` — Remove from _clips, returns True if deleted
  - `seed(clips: list[Clip]) -> None` — Populate repository with initial test data (deepcopies)

## Dependencies

- **stoat_ferret.db.models**: Clip dataclass
- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection and aiosqlite.Row
- **json**: For serializing/deserializing effects_json
- **datetime**: For Clip timestamp fields
- **copy**: For deepcopy isolation in in-memory repository
- **typing**: For type hints (Protocol, Any)

## Key Implementation Details

### JSON Serialization

- **effects** field: Serialized to `effects_json` (TEXT column)
  - None is stored as NULL
  - Deserialized back to list[dict] on retrieval
  - Example: `[{"type": "brightness", "value": 1.2}]`

### Timeline Columns

- Added via migration in schema.py:
  - `track_id` (TEXT) — Assigned track for this clip
  - `timeline_start` (REAL) — Start position on timeline (seconds or normalized units)
  - `timeline_end` (REAL) — End position on timeline
- Backward compatibility: Uses dict-style .get() for these columns
- Allows safe operation on databases that haven't been migrated yet

### Async/Await Pattern

- All public methods are async and must be awaited
- Uses `await self._conn.execute()`, `await cursor.fetchone()`, `await cursor.fetchall()` for database operations
- Uses `await self._conn.commit()` to persist changes

### Foreign Key Constraints

- clips table has references to:
  - `projects(id)` with ON DELETE CASCADE (deleting project deletes all clips)
  - `videos(id)` with ON DELETE RESTRICT (cannot delete source video if clips reference it)

### Deepcopy Isolation

- AsyncInMemoryClipRepository stores and returns deepcopies to prevent external mutations
- Prevents bugs where test code modifies returned objects and affects internal state

### Ordering

- list_by_project() returns clips sorted by timeline_position (legacy column)
- This maintains temporal order of clips on the timeline
- Could be extended to use track_id and timeline_start for more sophisticated ordering

## Relationships

- **Used by:**
  - FastAPI application lifespan (dependency injection in app.state)
  - Async service layer for clip metadata operations
  - API route handlers for clip endpoints (async route handlers)
  - timeline_repository.AsyncSQLiteTimelineRepository — for clip queries by track
  - Tests that need async clip repository behavior

- **Uses:**
  - models.Clip — the primary data model
  - schema (indirectly) — depends on clips table schema definition
  - json — for serialization/deserialization of effects

- **Associated entities:**
  - project_repository.AsyncSQLiteProjectRepository — clips belong to projects
  - Models.Video — source_video_id references videos table (RESTRICT delete)
  - Models.Track — track_id optional reference to timeline tracks
