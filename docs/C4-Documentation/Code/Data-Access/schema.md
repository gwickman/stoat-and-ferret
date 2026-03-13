# Schema

**Source:** `src/stoat_ferret/db/schema.py`
**Component:** Data Access

## Purpose

Defines the SQLite database schema including table definitions, indexes, FTS5 full-text search virtual tables, and database migration functions. Handles idempotent schema creation and column additions for backward compatibility. Provides both sync and async schema initialization functions.

## Public Interface

### Constants (Table Names)

- `TABLE_VIDEOS: str = "videos"`
- `TABLE_VIDEOS_FTS: str = "videos_fts"`
- `TABLE_AUDIT_LOG: str = "audit_log"`
- `TABLE_PROJECTS: str = "projects"`
- `TABLE_CLIPS: str = "clips"`
- `TABLE_TRACKS: str = "tracks"`
- `TABLE_PROJECT_VERSIONS: str = "project_versions"`

### SQL Definitions (DDL Strings)

- `VIDEOS_TABLE: str` — Creates videos table with path unique constraint
- `VIDEOS_PATH_INDEX: str` — Index on videos.path for lookups
- `VIDEOS_FTS: str` — FTS5 virtual table for full-text search on filename and path
- `VIDEOS_FTS_INSERT_TRIGGER: str` — Auto-sync FTS on INSERT
- `VIDEOS_FTS_DELETE_TRIGGER: str` — Auto-sync FTS on DELETE
- `VIDEOS_FTS_UPDATE_TRIGGER: str` — Auto-sync FTS on UPDATE
- `AUDIT_LOG_TABLE: str` — Audit log table with entity_id and timestamp index
- `AUDIT_LOG_INDEX: str` — Composite index on entity_id and timestamp
- `PROJECTS_TABLE: str` — Projects table with default output dimensions (1920x1080 @ 30fps)
- `CLIPS_TABLE: str` — Clips table with CASCADE delete on projects, RESTRICT on videos
- `CLIPS_PROJECT_INDEX: str` — Index for querying clips by project_id
- `CLIPS_TIMELINE_INDEX: str` — Composite index for timeline queries (project_id, timeline_position)
- `TRACKS_TABLE: str` — Tracks table for timeline track management
- `TRACKS_PROJECT_INDEX: str` — Index for querying tracks by project_id
- `PROJECT_VERSIONS_TABLE: str` — Version history table with UNIQUE(project_id, version_number)
- `PROJECT_VERSIONS_PROJECT_INDEX: str` — Composite index for version queries

### Column Definitions

- `CLIPS_TIMELINE_COLUMNS: list[tuple[str, str]]` — Optional columns for clip timeline positioning:
  - `("track_id", "TEXT")` — Track assignment
  - `("timeline_start", "REAL")` — Timeline start position
  - `("timeline_end", "REAL")` — Timeline end position

- `PROJECTS_AUDIO_MIX_COLUMNS: list[tuple[str, str]]` — Optional columns for projects:
  - `("audio_mix_json", "TEXT")` — Audio mix settings (JSON)

### Schema Creation Functions

- `create_tables(conn: sqlite3.Connection) -> None`
  - Creates all tables, indexes, triggers, and migrations synchronously
  - Handles idempotent schema creation (safe to call multiple times)
  - Parameters: `conn` — SQLite database connection

- `async create_tables_async(db: aiosqlite.Connection) -> None`
  - Async equivalent of create_tables()
  - Handles idempotent schema creation (safe to call multiple times)
  - Parameters: `db` — Async SQLite database connection

### Private Migration Functions (Internal)

- `_alter_projects_add_audio_mix_column(conn: sqlite3.Connection) -> None`
  - Adds audio_mix_json column to projects table if it doesn't exist
  - Silently ignores "duplicate column name" errors for idempotency

- `_alter_clips_add_timeline_columns(conn: sqlite3.Connection) -> None`
  - Adds timeline columns (track_id, timeline_start, timeline_end) to clips table
  - Silently ignores "duplicate column name" errors for idempotency

- `async _alter_projects_add_audio_mix_column_async(db: aiosqlite.Connection) -> None`
  - Async version of project audio_mix migration

- `async _alter_clips_add_timeline_columns_async(db: aiosqlite.Connection) -> None`
  - Async version of clips timeline migration

## Dependencies

- **sqlite3**: Python standard library for synchronous database operations
- **aiosqlite**: Async SQLite wrapper for async database operations

## Key Implementation Details

### FTS5 Full-Text Search

- Uses SQLite's FTS5 module for efficient text search on videos table
- Searches filename and path fields with "content" external content table pattern
- Triggers automatically keep FTS5 virtual table in sync with videos table (INSERT, UPDATE, DELETE)
- This allows search() operations on Video repository to be very efficient

### Foreign Key Constraints

- `clips` table has:
  - `ON DELETE CASCADE` for projects (deleting project cascades to clips)
  - `ON DELETE RESTRICT` for videos (cannot delete video with clips referencing it)
- `tracks` table has `ON DELETE CASCADE` for projects

### Migration Strategy

- Uses try/except with "duplicate column name" error detection for idempotent migrations
- Allows safely re-running schema creation on partially migrated databases
- Both sync and async versions provided for flexibility

### Table Schemas

**videos table:**
- Stores video metadata with path uniqueness constraint
- Supports frame rate as numerator/denominator for precision
- Nullable audio_codec and thumbnail_path for optional data

**projects table:**
- Default output dimensions: 1920x1080 at 30fps
- Stores transitions and audio_mix as JSON strings
- audio_mix_json column added via migration (initially NULL for existing records)

**clips table:**
- Stores clip references and positioning
- effects_json for effect parameters
- timeline_position for legacy ordering (superseded by track_id/timeline_start)
- track_id, timeline_start, timeline_end added via migration

**tracks table:**
- Stores timeline track definitions (video, audio, text)
- muted and locked stored as INTEGER (0/1) for SQLite boolean compatibility
- z_index determines layer ordering

**project_versions table:**
- Stores timeline snapshots with auto-incrementing version numbers per project
- UNIQUE constraint on (project_id, version_number) prevents duplicate versions
- Includes checksum for data integrity validation

**audit_log table:**
- Records all INSERT, UPDATE, DELETE operations
- Composite index on (entity_id, timestamp) for efficient history queries
- changes_json stores field-level changes as JSON

## Relationships

- **Used by:**
  - `repository.py` — SQLiteVideoRepository reads/writes from/to these schemas
  - `async_repository.py` — AsyncSQLiteVideoRepository uses async schema
  - `project_repository.py` — AsyncSQLiteProjectRepository CRUD
  - `clip_repository.py` — AsyncSQLiteClipRepository CRUD
  - `timeline_repository.py` — AsyncSQLiteTimelineRepository for tracks and clips
  - `version_repository.py` — AsyncSQLiteVersionRepository for versioning
  - `audit.py` — AuditLogger writes to audit_log table

- **Uses:**
  - SQLite3 database engine (no external dependencies)
