# API Schemas

**Source:** `src/stoat_ferret/api/schemas/`
**Component:** API Gateway

## Purpose

Pydantic response and request schemas for all API endpoints. Provides request validation, response serialization, and OpenAPI documentation via type hints.

## Public Interface

All schemas are Pydantic BaseModel subclasses with from_attributes=True for ORM deserialization where applicable.

### Video Schemas (video.py)

- `VideoResponse`: Single video with metadata (id, path, filename, duration_frames, frame_rate, dimensions, codecs, file_size, thumbnail_path, timestamps)
- `VideoListResponse`: Paginated list (videos, total, limit, offset)
- `VideoSearchResponse`: Search results (videos, total, query)
- `ScanRequest`: Directory scan request (path: str, recursive: bool=True)
- `ScanError`: Scan error for file (path: str, error: str)
- `ScanResponse`: Scan results summary (scanned, new, updated, skipped, errors list)

### Project Schemas (project.py)

- `ProjectCreate`: Create request (name: str min_length=1, output_width/height/fps with defaults)
- `ProjectResponse`: Single project (id, name, output_width/height/fps, timestamps)
- `ProjectListResponse`: Paginated list (projects, total)

### Clip Schemas (clip.py)

- `ClipCreate`: Create request (source_video_id, in_point/out_point/timeline_position: int >= 0)
- `ClipUpdate`: Update request (in_point/out_point/timeline_position: int | None)
- `ClipResponse`: Single clip (id, project_id, source_video_id, in/out_point, timeline_position, effects: list[dict], timestamps)
- `ClipListResponse`: List (clips, total)

### Job Schemas (job.py)

- `JobSubmitResponse`: Job submission (job_id: str)
- `JobStatusResponse`: Job status (job_id, status: str, progress: float | None, result: Any, error: str | None)

### Effect Schemas (effect.py)

- `EffectResponse`: Single effect (effect_type, name, description, parameter_schema: dict, ai_hints: dict, filter_preview: str)
- `EffectListResponse`: List (effects, total)
- `EffectApplyRequest`: Apply request (effect_type, parameters: dict)
- `EffectApplyResponse`: Applied effect (effect_type, parameters, filter_string)
- `EffectPreviewRequest`: Preview request (effect_type, parameters)
- `EffectPreviewResponse`: Preview (effect_type, filter_string)
- `EffectUpdateRequest`: Update (parameters: dict)
- `EffectDeleteResponse`: Delete (index: int, deleted_effect_type: str)
- `TransitionRequest`: Transition request (source_clip_id, target_clip_id, transition_type, parameters)
- `TransitionResponse`: Applied transition (source_clip_id, target_clip_id, transition_type, parameters, filter_string)

### Audio Schemas (audio.py)

- `TrackConfig`: Per-track audio config (volume: float, fade_in: float, fade_out: float)
- `AudioMixRequest`: Audio mix config (tracks: list[TrackConfig], master_volume: float, normalize: bool)
- `AudioMixResponse`: Audio mix result (filter_preview: str, tracks_configured: int)

### Batch Schemas (batch.py)

- `BatchJobConfig`: Single batch job (project_id, output_path, quality: str="medium")
- `BatchRequest`: Batch submission (jobs: list[BatchJobConfig] min_length=1)
- `BatchResponse`: Batch submission result (batch_id, jobs_queued, status)
- `BatchJobStatusResponse`: Per-job status (job_id, project_id, status, progress: float, error: str | None)
- `BatchProgressResponse`: Batch progress (batch_id, overall_progress, completed_jobs, failed_jobs, total_jobs, jobs: list)

### Compose Schemas (compose.py)

- `PositionModel`: Custom position (x, y, width, height: float normalized 0.0-1.0)
- `LayoutPresetResponse`: Preset metadata (name, description, ai_hint, min_inputs, max_inputs: int)
- `LayoutPresetListResponse`: Preset list (presets, total)
- `LayoutRequest`: Layout request (preset: str | None, positions: list[PositionModel] | None, input_count: int, output_width/height: int)
- `LayoutResponsePosition`: Positioned element (x, y, width, height, z_index: int)
- `LayoutResponse`: Layout result (positions: list[LayoutResponsePosition], filter_preview: str)

### Timeline Schemas (timeline.py)

- `TrackCreate`: Create track (track_type: str, label: str | None, z_index: int | None, muted: bool, locked: bool)
- `TrackResponse`: Track (id, project_id, track_type, label, z_index, muted, locked, clips: list)
- `TimelineClipCreate`: Add clip to timeline (clip_id, track_id, timeline_start, timeline_end: float)
- `TimelineClipUpdate`: Update positioning (track_id: str | None, timeline_start/end: float | None)
- `TimelineClipResponse`: Positioned clip (id, project_id, source_video_id, track_id, timeline_start/end, in_point, out_point)
- `TransitionCreate`: Transition request (clip_a_id, clip_b_id, transition_type, duration: float)
- `AdjustedClipPosition`: Computed position (input_index, timeline_start/end: float)
- `TransitionResponse`: Applied transition (id, transition_type, duration, filter_string, timeline_offset, clips: list[AdjustedClipPosition])
- `TimelineResponse`: Complete timeline (project_id, tracks: list, duration: float, version: int)

### Version Schemas (version.py)

- `VersionResponse`: Single version (version_number: int, created_at: str ISO, checksum: str)
- `VersionListResponse`: Version list (total, limit, offset, versions: list)
- `RestoreResponse`: Restore result (restored_version, new_version, message: str)

### Filesystem Schemas (filesystem.py)

- `DirectoryEntry`: Directory (name, path)
- `DirectoryListResponse`: Directory list (path, directories: list)

## Key Implementation Details

- **ORM compatibility**: from_attributes=True allows Pydantic to deserialize from domain model instances (Project, Video, Clip, etc.)

- **Type validation**: Field constraints (min_length, ge, le) provide request validation

- **Response serialization**: Pydantic models automatically serialize to JSON via FastAPI

- **OpenAPI integration**: Type hints automatically generate OpenAPI schema documentation

- **Nested models**: Complex structures use nested Pydantic models (e.g., ClipResponse contains list[dict] for effects)

- **Optional fields**: Use `| None` type hints for optional fields with defaults

- **Timestamp handling**: datetime fields automatically serialized to ISO 8601 strings

## Dependencies

### Internal Dependencies

None (schemas are standalone)

### External Dependencies

- `pydantic.BaseModel`: Base model class
- `pydantic.Field`: Field definition with constraints
- `pydantic.ConfigDict`: Model configuration
- `datetime.datetime`: Timestamp fields

## Relationships

- **Used by**: All routers for request validation and response serialization
- **Used by**: FastAPI for OpenAPI documentation generation
