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
- `TABLE_BATCH_JOBS: str = "batch_jobs"`
- `TABLE_PROXY_FILES: str = "proxy_files"`
- `TABLE_THUMBNAIL_STRIPS: str = "thumbnail_strips"`
- `TABLE_WAVEFORMS: str = "waveforms"`
- `TABLE_PREVIEW_SESSIONS: str = "preview_sessions"`
- `TABLE_RENDER_JOBS: str = "render_jobs"`
- `TABLE_RENDER_CHECKPOINTS: str = "render_checkpoints"`
- `TABLE_ENCODER_CACHE: str = "encoder_cache"`

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
- `BATCH_JOBS_TABLE: str` — Batch job records table with batch_id, job_id (unique), project_id, status, progress
- `BATCH_JOBS_BATCH_ID_INDEX: str` — Index for querying jobs by batch_id
- `PROXY_FILES_TABLE: str` — Proxy file records table with UNIQUE(source_video_id, quality)
- `PROXY_FILES_VIDEO_INDEX: str` — Index for querying proxies by source_video_id
- `THUMBNAIL_STRIPS_TABLE: str` — Thumbnail strip sprite sheet records with frame grid dimensions
- `THUMBNAIL_STRIPS_VIDEO_INDEX: str` — Index for querying strips by video_id
- `WAVEFORMS_TABLE: str` — Waveform metadata records with format (png/json) and duration
- `WAVEFORMS_VIDEO_INDEX: str` — Index for querying waveforms by video_id
- `PREVIEW_SESSIONS_TABLE: str` — Preview session records with status, HLS manifest tracking, TTL expiry
- `PREVIEW_SESSIONS_PROJECT_INDEX: str` — Index for querying sessions by project_id
- `PREVIEW_SESSIONS_EXPIRES_INDEX: str` — Index for querying expired sessions by expires_at
- `RENDER_JOBS_TABLE: str` — Render job records with status state machine, progress, retry_count
- `RENDER_JOBS_STATUS_INDEX: str` — Index for querying jobs by status (FIFO dequeue)
- `RENDER_JOBS_PROJECT_INDEX: str` — Index for querying jobs by project_id
- `RENDER_CHECKPOINTS_TABLE: str` — Write-once per-segment checkpoints for crash recovery
- `RENDER_CHECKPOINTS_JOB_INDEX: str` — Index for querying checkpoints by job_id
- `ENCODER_CACHE_TABLE: str` — Hardware encoder detection cache with codec and type info

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

**batch_jobs table:**
- Stores batch render job records with auto-incrementing row ID
- batch_id groups multiple jobs into a single batch operation
- job_id is unique across all jobs for individual job tracking
- status: queued, running, completed, failed (state machine enforced)
- progress: 0.0-1.0 float for render completion percentage
- error: NULL for success, contains message when status is failed
- created_at/updated_at track job lifecycle timestamps

**proxy_files table:**
- Stores proxy file metadata with unique constraint on (source_video_id, quality)
- status: pending, generating, ready, failed, stale (state machine enforced)
- source_checksum: SHA-256 of source video for validity checking
- generated_at: NULL until status transitions to ready
- last_accessed_at: Updated on every status change for LRU cache eviction
- file_size_bytes: Proxy file size on disk for cache management

**thumbnail_strips table:**
- Stores sprite sheet frame grid dimensions for timeline seek tooltips
- status: pending, generating, ready, error (state machine enforced)
- frame_width/frame_height: Pixel dimensions of each frame in the grid
- columns/rows: Grid layout of the sprite sheet
- interval_seconds: Seconds between extracted frames (temporal resolution)
- file_path: NULL until status is ready

**waveforms table:**
- Stores waveform generation metadata for audio visualization
- status: pending, generating, ready, error (state machine enforced)
- format: png or json output format
- duration: Audio duration in seconds
- channels: Number of audio channels
- file_path: NULL until status is ready

**preview_sessions table:**
- Stores HLS preview session records with TTL-based expiry
- status: initializing, generating, ready, seeking, error, expired (state machine enforced)
- quality_level: low, medium, high
- manifest_path: NULL until status transitions to ready
- segment_count: 0 until generation completes, then tracks HLS segment count
- expires_at: TTL timestamp for session cleanup
- error_message: NULL for success, contains error details when status is error
- Composite index on (project_id, expires_at) for efficient expiry queries

**render_jobs table:**
- Stores render job records with full lifecycle state machine
- status: QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED (state machine enforced via `validate_render_transition`)
- output_format: mp4, webm, mov, mkv
- quality_preset: draft, standard, high
- progress: 0.0-1.0 float for render completion
- error_message: NULL for success, contains failure details
- retry_count: Number of retry attempts (resets on manual retry)
- render_plan: JSON string containing the full render plan
- created_at/updated_at/completed_at: Lifecycle timestamps
- Indexes on status (for FIFO dequeue) and project_id (for project queries)

**render_checkpoints table:**
- Stores write-once per-segment completion records for crash recovery
- job_id: References render_jobs.id
- segment_index: Completed segment number
- completed_at: Timestamp of segment completion
- Index on job_id for recovery queries

**encoder_cache table:**
- Caches hardware encoder detection results to avoid repeated FFmpeg subprocess calls
- name: Encoder name (e.g., "h264_nvenc")
- codec: Codec family (e.g., "h264")
- is_hardware: Boolean flag
- encoder_type: Technology (e.g., "Nvenc", "QSV", "AMF", "VideoToolbox")
- detected_at: Detection timestamp for cache age tracking

## Relationships

- **Used by:**
  - `repository.py` — SQLiteVideoRepository reads/writes from/to videos, videos_fts
  - `async_repository.py` — AsyncSQLiteVideoRepository uses async schema
  - `project_repository.py` — AsyncSQLiteProjectRepository CRUD on projects
  - `clip_repository.py` — AsyncSQLiteClipRepository CRUD on clips
  - `timeline_repository.py` — AsyncSQLiteTimelineRepository for tracks and clips
  - `version_repository.py` — AsyncSQLiteVersionRepository for project_versions
  - `batch_repository.py` — AsyncSQLiteBatchRepository CRUD on batch_jobs
  - `preview_repository.py` — SQLitePreviewRepository CRUD on preview_sessions
  - `proxy_repository.py` — SQLiteProxyRepository CRUD on proxy_files
  - `audit.py` — AuditLogger writes to audit_log table
  - `render/render_repository.py` — AsyncSQLiteRenderRepository CRUD on render_jobs
  - `render/checkpoints.py` — CheckpointManager writes/reads render_checkpoints
  - `render/encoder_cache.py` — AsyncSQLiteEncoderCacheRepository manages encoder_cache

- **Uses:**
  - SQLite3 database engine (no external dependencies)
  - aiosqlite — async wrapper for async operations
