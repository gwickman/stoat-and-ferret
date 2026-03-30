# Models

**Source:** `src/stoat_ferret/db/models.py`
**Component:** Data Access

## Purpose

Defines all data model classes and exceptions for the database layer. These are Python dataclasses that represent database entities and serve as the primary data transfer objects between the repository layer and service/API layers. Includes domain validation logic for clips via the Rust core library.

## Public Interface

### Exceptions

- `ClipValidationError(field: str, message: str, actual: str | None = None, expected: str | None = None)`
  - Exception raised when clip validation fails. Wraps Rust validation error details.
  - `from_rust(err: RustClipValidationError) -> ClipValidationError`: Convert from Rust ClipValidationError
  - Properties: `field`, `message`, `actual`, `expected`

### Classes

- `Track`: Timeline track within a project
  - Properties:
    - `id: str` — Unique track identifier
    - `project_id: str` — Parent project ID
    - `track_type: str` — Type: "video", "audio", or "text"
    - `label: str` — Human-readable track label
    - `z_index: int` — Layer ordering (default 0)
    - `muted: bool` — Muted state (default False)
    - `locked: bool` — Locked state (default False)
  - `@staticmethod new_id() -> str`: Generate unique UUID for track

- `Clip`: Video clip segment on a timeline
  - Properties:
    - `id: str` — Unique clip identifier
    - `project_id: str` — Parent project ID
    - `source_video_id: str` — Reference to source video
    - `in_point: int` — Start frame in source video
    - `out_point: int` — End frame in source video
    - `timeline_position: int` — Position on timeline in frames
    - `created_at: datetime` — Creation timestamp
    - `updated_at: datetime` — Last update timestamp
    - `effects: list[dict[str, Any]] | None` — Optional effects list (JSON)
    - `track_id: str | None` — Assigned track (optional)
    - `timeline_start: float | None` — Timeline start position (optional)
    - `timeline_end: float | None` — Timeline end position (optional)
  - `@staticmethod new_id() -> str`: Generate unique UUID for clip
  - `validate(source_path: str, source_duration_frames: int | None = None) -> None`: Validate clip using Rust core, raises `ClipValidationError` on failure

- `Project`: Video editing project
  - Properties:
    - `id: str` — Unique project identifier
    - `name: str` — Project name
    - `output_width: int` — Output resolution width
    - `output_height: int` — Output resolution height
    - `output_fps: int` — Output frame rate
    - `created_at: datetime` — Creation timestamp
    - `updated_at: datetime` — Last update timestamp
    - `transitions: list[dict[str, Any]] | None` — Optional transition effects (JSON)
    - `audio_mix: dict[str, Any] | None` — Audio mix settings (JSON)
  - `@staticmethod new_id() -> str`: Generate unique UUID for project

- `AuditEntry`: Audit log entry tracking data modifications
  - Properties:
    - `id: str` — Unique audit entry identifier
    - `timestamp: datetime` — When the change occurred
    - `operation: str` — Type of operation: "INSERT", "UPDATE", or "DELETE"
    - `entity_type: str` — Type of entity changed (e.g., "video")
    - `entity_id: str` — ID of affected entity
    - `changes_json: str | None` — JSON serialization of field changes
    - `context: str | None` — Optional contextual information
  - `@staticmethod new_id() -> str`: Generate unique UUID for audit entry

- `Video`: Video metadata entity
  - Properties:
    - `id: str` — Unique video identifier
    - `path: str` — File system path (unique)
    - `filename: str` — File name only
    - `duration_frames: int` — Total frames in video
    - `frame_rate_numerator: int` — Numerator of frame rate fraction
    - `frame_rate_denominator: int` — Denominator of frame rate fraction
    - `width: int` — Video width in pixels
    - `height: int` — Video height in pixels
    - `video_codec: str` — Video codec name
    - `audio_codec: str | None` — Audio codec name (optional)
    - `file_size: int` — File size in bytes
    - `created_at: datetime` — Creation timestamp
    - `updated_at: datetime` — Last update timestamp
    - `thumbnail_path: str | None` — Path to thumbnail image (optional)
  - `@property frame_rate() -> float`: Computed frame rate as float (numerator / denominator)
  - `@property duration_seconds() -> float`: Computed duration in seconds (duration_frames / frame_rate)
  - `@staticmethod new_id() -> str`: Generate unique UUID for video

- `PreviewStatus`: Enum for preview session lifecycle
  - Values: `INITIALIZING`, `GENERATING`, `READY`, `SEEKING`, `ERROR`, `EXPIRED`
  - Transitions: initializing → generating → ready, ready ↔ seeking, any → error, any → expired
  - Terminal states: error (→ expired), expired (no further transitions)

- `PreviewQuality`: Enum for preview quality levels
  - Values: `LOW`, `MEDIUM`, `HIGH`

- `PreviewSession`: Preview session metadata for HLS preview generation
  - Properties:
    - `id: str` — Unique identifier (UUID)
    - `project_id: str` — FK to the project
    - `status: PreviewStatus` — Current lifecycle status
    - `quality_level: PreviewQuality` — Quality level of the preview
    - `created_at: datetime` — When the session was created
    - `updated_at: datetime` — When the session was last modified
    - `expires_at: datetime` — When the session expires (TTL)
    - `manifest_path: str | None` — Path to HLS manifest file (None until ready)
    - `segment_count: int` — Number of HLS segments generated (default 0)
    - `error_message: str | None` — Error description (None on success)
  - `@staticmethod new_id() -> str`: Generate unique UUID for preview session

- `ThumbnailStripStatus`: Enum for thumbnail strip lifecycle
  - Values: `PENDING`, `GENERATING`, `READY`, `ERROR`
  - Transitions: pending → generating → ready, any → error

- `ThumbnailStrip`: Thumbnail strip sprite sheet metadata
  - Represents an NxM grid sprite sheet generated from a video for timeline seek tooltips
  - Properties:
    - `id: str` — Unique identifier (UUID)
    - `video_id: str` — FK to the source video
    - `status: ThumbnailStripStatus` — Current lifecycle status
    - `created_at: datetime` — When the strip was created
    - `file_path: str | None` — Path to the sprite sheet JPEG (None until ready)
    - `frame_count: int` — Number of frames in the sprite sheet (default 0)
    - `frame_width: int` — Width of each frame in pixels (default 160)
    - `frame_height: int` — Height of each frame in pixels (default 90)
    - `interval_seconds: float` — Seconds between extracted frames (default 5.0)
    - `columns: int` — Number of columns in the grid (default 10)
    - `rows: int` — Number of rows in the grid (default 0)
  - `@staticmethod new_id() -> str`: Generate unique UUID for thumbnail strip

- `WaveformStatus`: Enum for waveform lifecycle
  - Values: `PENDING`, `GENERATING`, `READY`, `ERROR`
  - Transitions: pending → generating → ready, any → error

- `WaveformFormat`: Enum for waveform output format
  - Values: `PNG`, `JSON`

- `Waveform`: Waveform metadata for audio visualization
  - Represents a waveform generated from a video's audio stream
  - Properties:
    - `id: str` — Unique identifier (UUID)
    - `video_id: str` — FK to the source video
    - `format: WaveformFormat` — Output format (png or json)
    - `status: WaveformStatus` — Current lifecycle status
    - `created_at: datetime` — When the waveform was created
    - `file_path: str | None` — Path to the output file (None until ready)
    - `duration: float` — Audio duration in seconds (default 0.0)
    - `channels: int` — Number of audio channels (default 0)
  - `@staticmethod new_id() -> str`: Generate unique UUID for waveform

- `ProxyStatus`: Enum for proxy file lifecycle
  - Values: `PENDING`, `GENERATING`, `READY`, `FAILED`, `STALE`
  - Transitions: pending → generating → (ready | failed), ready → stale

- `ProxyQuality`: Enum for proxy quality levels
  - Values: `LOW`, `MEDIUM`, `HIGH`

- `ProxyFile`: Proxy file metadata for lower-resolution editing previews
  - Represents a proxy file generated from a source video at a specific quality level
  - Each (source_video_id, quality) pair is unique
  - Properties:
    - `id: str` — Unique identifier (UUID)
    - `source_video_id: str` — FK to the source video
    - `quality: ProxyQuality` — Quality level of the proxy
    - `file_path: str` — Absolute path to the proxy file
    - `file_size_bytes: int` — Size of the proxy file in bytes
    - `status: ProxyStatus` — Current lifecycle status
    - `source_checksum: str` — SHA-256 checksum of the source video
    - `generated_at: datetime | None` — When generation completed (None until ready)
    - `last_accessed_at: datetime` — When the proxy was last accessed
  - `@staticmethod new_id() -> str`: Generate unique UUID for proxy file

## Dependencies

- **stoat_ferret_core**: Rust core library bindings
  - `ClipValidationError` (Rust type, wrapped as Python exception)
  - `Clip` (Rust type for validation)
  - `Duration` (Rust type)
  - `Position` (Rust type)
  - `validate_clip()` (Rust function)
- **datetime**: Python standard library for timestamp handling
- **uuid**: Python standard library for ID generation
- **dataclasses**: Python standard library for dataclass definitions

## Key Implementation Details

- All models are dataclasses with sensible defaults for optional fields
- Each model has a `new_id()` static method generating UUIDs for database primary keys
- `Clip.validate()` bridges to Rust core library validation, converting between Python and Rust types
- Complex data structures (effects, transitions, audio_mix) are stored as JSON strings in the database but represented as Python dicts in the models
- Video frame rate is represented as a numerator/denominator pair to maintain precision for common frame rates (24, 23.976, 25, 29.97, 30, 50, 59.94, 60)
- Timestamps use Python `datetime` objects but are serialized to ISO format strings for storage

## Relationships

- **Used by:**
  - `repository.py` (SQLiteVideoRepository) — converts Video models to/from database rows
  - `async_repository.py` (AsyncSQLiteVideoRepository) — async conversions
  - `project_repository.py` (AsyncSQLiteProjectRepository) — Project CRUD operations
  - `clip_repository.py` (AsyncSQLiteClipRepository) — Clip CRUD operations
  - `timeline_repository.py` (AsyncSQLiteTimelineRepository) — Track CRUD and Clip queries
  - `version_repository.py` — indirectly (uses JSON for timeline data)
  - `batch_repository.py` (AsyncSQLiteBatchRepository) — BatchJobRecord for batch render jobs
  - `preview_repository.py` (SQLitePreviewRepository) — PreviewSession, PreviewStatus, PreviewQuality
  - `proxy_repository.py` (SQLiteProxyRepository) — ProxyFile, ProxyStatus, ProxyQuality
  - `audit.py` (AuditLogger) — logs changes to these models
  - API layer (routes and handlers) — transmits models to/from clients

- **Uses:**
  - stoat_ferret_core library for clip validation
  - enum.Enum — for status and quality enumerations
  - uuid — for generating unique IDs via new_id() methods
