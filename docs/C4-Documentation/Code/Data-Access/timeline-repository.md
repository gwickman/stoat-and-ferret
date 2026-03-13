# Timeline Repository

**Source:** `src/stoat_ferret/db/timeline_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for timeline management, including track CRUD operations and clip queries by track. Defines AsyncTimelineRepository protocol and offers two implementations: AsyncSQLiteTimelineRepository for production use and AsyncInMemoryTimelineRepository for testing. Manages the hierarchical relationship between tracks and clips.

## Public Interface

### Protocols

- `AsyncTimelineRepository`
  - Abstract protocol defining asynchronous timeline repository operations for tracks and clips
  - Methods:
    - `async create_track(track: Track) -> Track` — Create a track, raises ValueError if duplicate ID or foreign key violation
    - `async get_track(track_id: str) -> Track | None` — Get track by ID
    - `async get_tracks_by_project(project_id: str) -> list[Track]` — List all tracks in a project, ordered by z_index
    - `async update_track(track: Track) -> Track` — Update existing track, raises ValueError if not found
    - `async delete_track(track_id: str) -> bool` — Delete track by ID, returns True if deleted
    - `async get_clips_by_track(track_id: str) -> list[Clip]` — Get clips assigned to track, ordered by timeline_start
    - `async count_tracks(project_id: str) -> int` — Return number of tracks in a project
    - `async count_clips(project_id: str) -> int` — Return number of clips in a project

### Classes

- `AsyncSQLiteTimelineRepository`
  - Async SQLite implementation of AsyncTimelineRepository protocol
  - `__init__(conn: aiosqlite.Connection) -> None`
    - Initialize with async SQLite connection
  - `async create_track(track: Track) -> Track` — INSERT into tracks table
    - Converts muted and locked bools to integers (0/1) for SQLite
    - Raises ValueError on IntegrityError (duplicate ID or foreign key violation)
  - `async get_track(track_id: str) -> Track | None` — SELECT by id
  - `async get_tracks_by_project(project_id: str) -> list[Track]` — SELECT all tracks for project, ordered by z_index
  - `async update_track(track: Track) -> Track` — UPDATE label, muted, locked for given track_id
    - Converts bool fields to integers for storage
    - Raises ValueError if track not found (rowcount == 0)
  - `async delete_track(track_id: str) -> bool` — DELETE by id, returns True if deleted
  - `async get_clips_by_track(track_id: str) -> list[Clip]` — SELECT all clips with track_id, ordered by timeline_start
  - `async count_tracks(project_id: str) -> int` — SELECT COUNT(*) for tracks in project
  - `async count_clips(project_id: str) -> int` — SELECT COUNT(*) for clips in project
  - `_row_to_track(row: Any) -> Track` — Convert database row to Track object (sync helper)
    - Converts integer muted/locked fields back to bool
  - `_row_to_clip(row: Any) -> Clip` — Convert database row to Clip object (sync helper)
    - Deserializes effects_json
    - Uses dict-style .get() for timeline columns (backward compatibility)

- `AsyncInMemoryTimelineRepository`
  - Async in-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains two indices: `_tracks` (id → Track) and `_clips` (id → Clip)
  - `__init__() -> None` — Initialize empty storage
  - `async create_track(track: Track) -> Track` — Store deepcopy in _tracks
    - Raises ValueError if track ID already exists
  - `async get_track(track_id: str) -> Track | None` — Retrieve deepcopy from _tracks
  - `async get_tracks_by_project(project_id: str) -> list[Track]` — Return deepcopies filtered by project_id, sorted by z_index
  - `async update_track(track: Track) -> Track` — Update _tracks with deepcopy
    - Raises ValueError if track not found
  - `async delete_track(track_id: str) -> bool` — Remove from _tracks, returns True if deleted
  - `async get_clips_by_track(track_id: str) -> list[Clip]` — Return deepcopies of clips filtered by track_id, sorted by timeline_start
    - Uses custom sort key: `timeline_start` or 0.0 if None
  - `async count_tracks(project_id: str) -> int` — Return count of tracks in project
  - `async count_clips(project_id: str) -> int` — Return count of clips in project
  - `seed(tracks: list[Track], clips: list[Clip] | None = None) -> None` — Populate repository with test data (deepcopies)

## Dependencies

- **stoat_ferret.db.models**: Track and Clip dataclasses
- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection and aiosqlite.Row
- **json**: For deserializing effects_json (imported in _row_to_clip)
- **datetime**: For Clip timestamp fields (imported in _row_to_clip)
- **copy**: For deepcopy isolation in in-memory repository
- **typing**: For type hints (Protocol, Any)

## Key Implementation Details

### Track Fields

- **id**: UUID string (primary key)
- **project_id**: Foreign key to projects (ON DELETE CASCADE)
- **track_type**: "video", "audio", or "text" — determines track purpose
- **label**: Human-readable name (e.g., "Background Music", "Subtitle Track")
- **z_index**: Integer defining layer order (0 is lowest, higher values on top)
- **muted**: Boolean (stored as 0/1 INTEGER in SQLite)
- **locked**: Boolean (stored as 0/1 INTEGER in SQLite)

### Track Ordering

- get_tracks_by_project() returns tracks sorted by z_index ascending
- Lower z_index values appear at bottom of track stack
- Higher z_index values appear on top

### Clip Queries by Track

- get_clips_by_track() returns clips assigned to a track sorted by timeline_start
- Uses timeline_start column for ordering (added via schema migration)
- Handles NULL timeline_start by treating as 0.0 for sorting

### Count Operations

- count_tracks() and count_clips() provide aggregation per project
- Useful for UI validation and data consistency checks

### Async/Await Pattern

- All public methods are async and must be awaited
- Uses `await self._conn.execute()`, `await cursor.fetchone()`, `await cursor.fetchall()` for database operations
- Uses `await self._conn.commit()` to persist changes

### Deepcopy Isolation

- AsyncInMemoryTimelineRepository stores and returns deepcopies to prevent external mutations
- Prevents bugs where test code modifies returned objects and affects internal state

### Foreign Key Constraints

- tracks table has reference to projects(id) with ON DELETE CASCADE
- Deleting a project automatically deletes all its tracks
- Clips reference both projects and tracks; deleting track does not delete clips (clips can be reassigned)

### Boolean Conversion

- SQLite doesn't have native boolean type; uses INTEGER (0/1)
- create_track() and update_track() convert Python bool to int
- _row_to_track() converts int back to bool

## Relationships

- **Used by:**
  - FastAPI application lifespan (dependency injection in app.state)
  - Async service layer for timeline management
  - API route handlers for track and timeline endpoints
  - Tests that need async timeline repository behavior

- **Uses:**
  - models.Track — track data model
  - models.Clip — clip data model
  - schema (indirectly) — depends on tracks and clips table schemas

- **Associated entities:**
  - project_repository.AsyncSQLiteProjectRepository — tracks belong to projects
  - clip_repository.AsyncSQLiteClipRepository — clips can be assigned to tracks
