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
  - `audit.py` (AuditLogger) — logs changes to these models
  - API layer (routes and handlers) — transmits models to/from clients

- **Uses:**
  - stoat_ferret_core library for clip validation
