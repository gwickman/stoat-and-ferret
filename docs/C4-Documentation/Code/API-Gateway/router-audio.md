# Audio Router

**Source:** `src/stoat_ferret/api/routers/audio.py`
**Component:** API Gateway

## Purpose

Audio mix configuration and preview endpoints. Manages per-track volume, fade, and master volume settings with FFmpeg filter chain generation via Rust AudioMixSpec and VolumeBuilder.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| PUT | /api/v1/projects/{project_id}/audio/mix | Configure audio mix for project |
| POST | /api/v1/audio/mix/preview | Preview audio mix filter chain |

### Functions

- `configure_audio_mix(project_id: str, request: AudioMixRequest, http_request: Request, project_repo: ProjectRepoDep) -> AudioMixResponse`: Configures audio mix for project. Validates project exists, track count 2-8, per-track volume 0.0-2.0, master volume 0.0-2.0. Builds filter preview via Rust. Persists mix config on project. Broadcasts AUDIO_MIX_CHANGED event. Returns filter preview and track count. 404 if project not found, 422 if validation fails.

- `preview_audio_mix(request: AudioMixRequest) -> AudioMixResponse`: Previews audio mix filter chain without persisting. Validates all parameters. Builds and returns filter preview. 422 if validation fails.

### Helper Functions

- `_validate_volumes(tracks: list[TrackConfig], master_volume: float) -> None`: Validates all track volumes and master volume in range [0.0, 2.0]. Raises 422 if out of range with specific track/value in message.

- `_validate_track_count(tracks: list[TrackConfig]) -> None`: Validates track count is 2-8. Raises 422 if out of range.

- `_build_filter_preview(request: AudioMixRequest) -> str`: Builds FFmpeg filter chain from Rust AudioMixSpec (tracks with volume/fade) and VolumeBuilder (master volume). Concatenates with semicolon if master volume != 1.0.

### Dependency Functions

- `_get_project_repository(request: Request) -> AsyncProjectRepository`

## Key Implementation Details

- **Rust integration**: AudioMixSpec takes list of TrackAudioConfig (volume, fade_in, fade_out); builds_filter_chain() generates initial filter. VolumeBuilder wraps master volume multiplier.
- **Volume ranges**: All volumes clamped to [0.0, 2.0]; 1.0 is unity (no change), 0.0 is mute, >1.0 is amplification
- **Fade support**: Per-track fade_in and fade_out stored as fields on TrackConfig/TrackAudioConfig
- **Filter composition**: Multiple filters concatenated with semicolon (FFmpeg filter chain syntax)
- **Storage**: Audio mix persists as dict on project with keys: tracks, master_volume, normalize, filter_preview
- **WebSocket broadcast**: AUDIO_MIX_CHANGED event includes project_id and tracks_configured count
- **Stateless preview**: preview_audio_mix endpoint has no project_id; purely functional (preview without side effects)

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.audio.*`: AudioMixRequest, AudioMixResponse, TrackConfig
- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket manager
- `stoat_ferret.db.project_repository.AsyncProjectRepository, AsyncSQLiteProjectRepository`: Project persistence
- `stoat_ferret_core.*`: AudioMixSpec, TrackAudioConfig, VolumeBuilder (Rust bindings)

### External Dependencies

- `fastapi`: APIRouter, Depends, HTTPException, Request, status
- `datetime.datetime, datetime.timezone`: Timestamps
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Project repository, Rust core for audio filter generation, WebSocket manager for broadcasting
