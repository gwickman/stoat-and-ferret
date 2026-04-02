# Data Access

## Purpose

The Data Access component provides the full persistence layer for the stoat-and-ferret backend. It defines protocol-based repository interfaces for every domain entity (videos, projects, clips, timeline tracks, project versions, batch jobs, preview sessions, proxy files, and audit entries), implements them against an async SQLite database, manages schema creation and backward-compatible migrations, and provides an immutable audit trail for all data mutations.

## Responsibilities

- Define protocol interfaces for asynchronous CRUD operations on all domain entities
- Implement SQLite-backed production repositories using `aiosqlite` for non-blocking I/O
- Implement in-memory repositories for deterministic testing without database overhead
- Initialize and migrate the database schema idempotently on startup
- Enforce referential integrity via foreign key constraints and cascade delete rules
- Support full-text search on videos using SQLite FTS5 with automatic trigger-based sync
- Record an append-only audit trail of INSERT, UPDATE, and DELETE operations
- Manage project version history with non-destructive restoration and SHA-256 checksums
- Serialize complex domain fields (effects, transitions, audio mix) as JSON columns
- Track batch job lifecycle with status state machine (queued → running → completed/failed)
- Manage preview session records with TTL-based expiry and HLS manifest metadata
- Track proxy file records with LRU access timestamps and cache statistics
- Store thumbnail strip and waveform generation metadata
- Store render job records with status state machine, progress tracking, and retry counts
- Store write-once render segment checkpoints for crash recovery
- Store hardware encoder detection cache for render subsystem

## Interfaces

### Provided Interfaces

**AsyncVideoRepository (protocol)**
- `add(video: Video) -> Video`
- `get(id: str) -> Video | None`
- `get_by_path(path: str) -> Video | None`
- `list_videos(limit: int, offset: int) -> list[Video]`
- `search(query: str, limit: int) -> list[Video]` — FTS5 prefix search on filename and path
- `update(video: Video) -> Video`
- `count() -> int`
- `delete(id: str) -> bool`

**AsyncProjectRepository (protocol)**
- `add(project: Project) -> Project`
- `get(id: str) -> Project | None`
- `list_projects(limit: int, offset: int) -> list[Project]`
- `update(project: Project) -> Project`
- `delete(id: str) -> bool`
- `count() -> int` — FR-002 project count tracking

**AsyncClipRepository (protocol)**
- `add(clip: Clip) -> Clip`
- `get(id: str) -> Clip | None`
- `list_by_project(project_id: str) -> list[Clip]`
- `update(clip: Clip) -> Clip`
- `delete(id: str) -> bool`

**AsyncTimelineRepository (protocol)**
- `create_track(track: Track) -> Track`
- `get_track(track_id: str) -> Track | None`
- `get_tracks_by_project(project_id: str) -> list[Track]` — ordered by z_index
- `update_track(track: Track) -> Track`
- `delete_track(track_id: str) -> bool`
- `get_clips_by_track(track_id: str) -> list[Clip]` — ordered by timeline_start
- `count_tracks(project_id: str) -> int`
- `count_clips(project_id: str) -> int`

**AsyncVersionRepository (protocol)**
- `save(project_id: str, timeline_json: str) -> VersionRecord` — auto-increments version number
- `list_versions(project_id: str) -> list[VersionRecord]` — newest first
- `get_version(project_id: str, version_number: int) -> VersionRecord | None`
- `restore(project_id: str, version_number: int) -> VersionRecord` — non-destructive; creates new version

**AsyncBatchRepository (protocol)**
- `create_job(batch_id: str, job_type: str, payload: dict) -> BatchJobRecord`
- `get_job(job_id: str) -> BatchJobRecord | None`
- `list_by_batch(batch_id: str) -> list[BatchJobRecord]`
- `update_status(job_id: str, status: str, progress: float | None, error: str | None) -> BatchJobRecord`

**AsyncPreviewRepository (protocol)**
- `create(session: PreviewSession) -> PreviewSession`
- `get(session_id: str) -> PreviewSession | None`
- `update(session: PreviewSession) -> PreviewSession`
- `delete(session_id: str) -> bool`
- `list_expired() -> list[PreviewSession]` — sessions past TTL
- `count_active() -> int`

**AsyncProxyRepository (protocol)**
- `create(proxy: ProxyFile) -> ProxyFile`
- `get(proxy_id: str) -> ProxyFile | None`
- `get_by_video(video_id: str, quality: str | None) -> ProxyFile | None`
- `update(proxy: ProxyFile) -> ProxyFile`
- `delete(proxy_id: str) -> bool`
- `list_by_access(limit: int) -> list[ProxyFile]` — LRU order for eviction
- `cache_stats() -> dict` — count, total size, oldest access time

**AuditLogger**
- `log_change(operation: str, entity_type: str, entity_id: str, changes: dict | None, context: str | None) -> AuditEntry`
- `get_history(entity_id: str, limit: int) -> list[AuditEntry]`

**Schema Functions**
- `create_tables(conn: sqlite3.Connection) -> None` — synchronous schema initialization
- `create_tables_async(db: aiosqlite.Connection) -> None` — async schema initialization

### Required Interfaces

- **Rust Core component** — `Clip.validate()` in `models.py` delegates to `validate_clip()` from `stoat_ferret_core` for clip in/out point validation against source video duration

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Models | `src/stoat_ferret/db/models.py` | Dataclasses for all entities: `Video`, `Project`, `Clip`, `Track`, `AuditEntry`, `PreviewSession`, `ThumbnailStrip`, `Waveform`, `ProxyFile`; status enums: `PreviewStatus`, `PreviewQuality`, `ThumbnailStripStatus`, `WaveformStatus`, `WaveformFormat`, `ProxyStatus`, `ProxyQuality`; `ClipValidationError` wrapping Rust validation errors |
| Schema | `src/stoat_ferret/db/schema.py` | DDL for all tables (videos, projects, clips, tracks, audit_log, project_versions, batch_jobs, proxy_files, thumbnail_strips, waveforms, preview_sessions, render_jobs, render_checkpoints, encoder_cache), indexes, FTS5 virtual table and triggers, backward-compatible column migrations |
| Async Video Repository | `src/stoat_ferret/db/async_repository.py` | `AsyncSQLiteVideoRepository` (production), `AsyncInMemoryVideoRepository` (testing) |
| Sync Video Repository | `src/stoat_ferret/db/repository.py` | `SQLiteVideoRepository` (sync, with field-level audit diff), `InMemoryVideoRepository` (testing) |
| Project Repository | `src/stoat_ferret/db/project_repository.py` | `AsyncSQLiteProjectRepository`, `AsyncInMemoryProjectRepository`; handles JSON serialization of transitions and audio_mix fields |
| Clip Repository | `src/stoat_ferret/db/clip_repository.py` | `AsyncSQLiteClipRepository`, `AsyncInMemoryClipRepository`; handles JSON effects field and timeline positioning columns |
| Timeline Repository | `src/stoat_ferret/db/timeline_repository.py` | `AsyncSQLiteTimelineRepository`, `AsyncInMemoryTimelineRepository`; track CRUD and clips-by-track queries |
| Version Repository | `src/stoat_ferret/db/version_repository.py` | `AsyncSQLiteVersionRepository`, `AsyncInMemoryVersionRepository`; versioning with SHA-256 checksums and non-destructive restore |
| Batch Repository | `src/stoat_ferret/db/batch_repository.py` | `AsyncSQLiteBatchRepository`, `InMemoryBatchRepository`; batch job tracking with status state machine |
| Preview Repository | `src/stoat_ferret/db/preview_repository.py` | `SQLitePreviewRepository`, `InMemoryPreviewRepository`; preview session lifecycle with TTL expiry |
| Proxy Repository | `src/stoat_ferret/db/proxy_repository.py` | `SQLiteProxyRepository`, `InMemoryProxyRepository`; proxy file tracking with LRU access and cache statistics |
| Audit | `src/stoat_ferret/db/audit.py` | `AuditLogger` — append-only audit trail with field-level change diffs stored as JSON |

## Key Behaviors

**Protocol-Based Design:** Every repository is defined as a Python `Protocol`, enabling structural subtyping. The API Gateway depends only on the protocol, not on any specific SQLite implementation. This makes the swap to an in-memory implementation in tests transparent.

**Idempotent Schema Migration:** `create_tables` and `create_tables_async` use try/except on "duplicate column name" errors to add new columns to existing databases. This allows safe re-execution on partially migrated databases without manual migration tooling.

**FTS5 Full-Text Search:** The `videos_fts` virtual table is kept in sync via INSERT, UPDATE, and DELETE triggers on the `videos` table. Searches use the `"query"*` prefix pattern to support incremental query matching.

**JSON Field Serialization:** Complex fields — clip effects, project transitions, project audio_mix — are stored as TEXT JSON columns. All repository implementations serialize on write and deserialize on read using Python's `json` module.

**Cascade Delete Policy:** Deleting a project cascades to its clips and tracks. Deleting a project cascades to its version records. Clips reference videos with `ON DELETE RESTRICT`; a video cannot be deleted if any clip references it.

**Timeline Columns via Migration:** The `track_id`, `timeline_start`, and `timeline_end` columns on the clips table were added via `ALTER TABLE ADD COLUMN`. Row-to-Clip deserialization uses dict-style `.get()` to handle rows from databases that have not yet been migrated.

**Checksum Integrity:** The version repository computes SHA-256 of the timeline JSON before saving. Restore operations verify the checksum of the source version before copying it into a new version record.

## Inter-Component Relationships

```
API Gateway
    |-- uses all repositories --> Data Access
    |-- uses AuditLogger --> Data Access

Data Access
    |-- uses Rust Core --> (Clip.validate() calls stoat_ferret_core.validate_clip)

Data Access
    |-- writes to --> SQLite database file (data/stoat.db by default)
```

## Version History

| Version | Changes |
|---------|---------|
| v012 | Added audio_mix_json column to projects table via migration; added `project_repository.md` |
| v013 | Added timeline columns (track_id, timeline_start, timeline_end) to clips table via migration; added `timeline-repository.md` |
| v016 | Added `version-repository.md` (project versioning with non-destructive restore and SHA-256 checksums); added `clip-repository.md` |
| v027 | Added batch, preview, and proxy repositories; expanded models with PreviewSession, ThumbnailStrip, Waveform, ProxyFile and status enums; added batch_jobs, proxy_files, thumbnail_strips, waveforms, preview_sessions tables to schema |
| v029 | Added render_jobs, render_checkpoints, encoder_cache tables to schema; Render Engine component owns its own repositories (AsyncRenderRepository, CheckpointManager, AsyncEncoderCacheRepository) |
