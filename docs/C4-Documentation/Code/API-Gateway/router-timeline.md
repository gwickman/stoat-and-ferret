# Timeline Router

**Source:** `src/stoat_ferret/api/routers/timeline.py`
**Component:** API Gateway

## Purpose

Timeline management endpoints for tracks, clip positioning, and transitions. Manages project timelines with track creation/deletion, clip assignment to tracks, timeline positioning, and transition application between adjacent clips.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| PUT | /api/v1/projects/{project_id}/timeline | Create or replace timeline tracks |
| GET | /api/v1/projects/{project_id}/timeline | Get complete timeline |
| POST | /api/v1/projects/{project_id}/timeline/clips | Assign clip to track with positioning |
| PATCH | /api/v1/projects/{project_id}/timeline/clips/{clip_id} | Update clip timeline position |
| DELETE | /api/v1/projects/{project_id}/timeline/clips/{clip_id} | Remove clip from timeline |
| POST | /api/v1/projects/{project_id}/timeline/transitions | Apply transition between adjacent clips |
| DELETE | /api/v1/projects/{project_id}/timeline/transitions/{transition_id} | Remove transition and recalculate duration |

### Functions

- `put_timeline(project_id: str, tracks_data: list[TrackCreate], request: Request, project_repo: ProjectRepoDep, timeline_repo: TimelineRepoDep, clip_repo: ClipRepoDep) -> TimelineResponse`: Replaces all tracks for project. Deletes existing tracks, creates new ones with z_index. Broadcasts TIMELINE_UPDATED. 404 if project not found.

- `get_timeline(project_id: str, project_repo: ProjectRepoDep, timeline_repo: TimelineRepoDep, clip_repo: ClipRepoDep) -> TimelineResponse`: Returns complete timeline with tracks ordered by z_index and clips ordered by timeline_start. Calculates duration from max clip end time. 404 if project not found.

- `add_timeline_clip(project_id: str, request: TimelineClipCreate, http_request: Request, project_repo: ProjectRepoDep, timeline_repo: TimelineRepoDep, clip_repo: ClipRepoDep) -> TimelineClipResponse`: Assigns clip to track with timeline positioning. Validates project/track/clip exist, timeline_start < timeline_end. Updates clip with track_id, timeline_start, timeline_end. Broadcasts TIMELINE_UPDATED. 404 if project/track/clip not found, 422 if positions invalid.

- `update_timeline_clip(project_id: str, clip_id: str, request: TimelineClipUpdate, http_request: Request, project_repo: ProjectRepoDep, timeline_repo: TimelineRepoDep, clip_repo: ClipRepoDep) -> TimelineClipResponse`: Updates clip timeline position/track. Validates new track if provided. Revalidates final positions. 404 if project/track/clip not found, 422 if positions invalid.

- `remove_timeline_clip(project_id: str, clip_id: str, request: Request, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> Response`: Clears clip's timeline association (track_id, timeline_start, timeline_end) without deleting clip. 204 No Content on success, 404 if project/clip not found.

- `add_transition(project_id: str, request: TransitionCreate, http_request: Request, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> TransitionResponse`: Applies transition between adjacent clips. Validates clips exist/belong to project, on same track, adjacent (clip_a.timeline_end == clip_b.timeline_start). Calls Rust calculate_composition_positions() to compute timeline offset. Calls build_composition_graph() to generate filter_string. Stores transition in project. Broadcasts TRANSITION_APPLIED. 404 if project/clips not found, 422 if not adjacent.

- `delete_transition(project_id: str, transition_id: str, request: Request, project_repo: ProjectRepoDep, timeline_repo: TimelineRepoDep, clip_repo: ClipRepoDep) -> TimelineResponse`: Removes transition. Recalculates timeline duration using Rust calculate_timeline_duration() with remaining transitions. Returns updated timeline. 404 if project/transition not found.

### Helper Functions

- `_build_timeline_response(project_id: str, tracks: list[Track], clips_by_track: dict[str, list[TimelineClipResponse]]) -> TimelineResponse`: Builds TimelineResponse from tracks and clips_by_track mapping
- `_get_clips_by_track(clip_repo: AsyncClipRepository, project_id: str) -> dict[str, list[TimelineClipResponse]]`: Groups clips by track_id and sorts by timeline_start
- `_broadcast(request: Request, event_type: EventType, payload: dict[str, Any]) -> None`: Broadcasts WebSocket event if ws_manager available

### Dependency Functions

- `get_timeline_repository(request: Request) -> AsyncTimelineRepository`
- `get_project_repository(request: Request) -> AsyncProjectRepository`
- `get_clip_repository(request: Request) -> AsyncClipRepository`

## Key Implementation Details

- **Clip positioning**: Clips have track_id, timeline_start, timeline_end fields for sequencing on timeline
- **Track management**: Tracks have z_index for layering (video/audio separation); clips on same track are sequenced
- **Adjacency check**: Transitions require clips on same track with clip_a.timeline_end == clip_b.timeline_start
- **Rust composition**: Transition application uses Rust CompositionClip, TransitionSpec, calculate_composition_positions(), build_composition_graph() for offset and filter computation
- **Duration calculation**: Timeline duration computed from max clip end time plus any transition offsets
- **WebSocket broadcast**: TIMELINE_UPDATED and TRANSITION_APPLIED events broadcast to all clients with project_id and optional clip/transition IDs
- **Transitions storage**: Stored as dicts on project.transitions with keys: id, clip_a_id, clip_b_id, transition_type, duration

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.timeline.*`: AdjustedClipPosition, TimelineClipCreate, TimelineClipResponse, TimelineClipUpdate, TimelineResponse, TrackCreate, TrackResponse, TransitionCreate, TransitionResponse
- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket manager
- `stoat_ferret.db.clip_repository.AsyncClipRepository, AsyncSQLiteClipRepository`: Clip persistence
- `stoat_ferret.db.models.Track`: Track domain model
- `stoat_ferret.db.project_repository.AsyncProjectRepository, AsyncSQLiteProjectRepository`: Project persistence
- `stoat_ferret.db.timeline_repository.AsyncTimelineRepository, AsyncSQLiteTimelineRepository`: Timeline persistence
- `stoat_ferret_core.*`: CompositionClip, TransitionSpec, TransitionType, build_composition_graph, calculate_composition_positions, calculate_timeline_duration (Rust bindings)

### External Dependencies

- `fastapi`: APIRouter, Depends, HTTPException, Request, Response, status
- `uuid.uuid4`: Transition ID generation
- `datetime.datetime, datetime.timezone`: Timestamps
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Timeline/project/clip repositories, Rust core for composition/transition calculation, WebSocket manager for broadcasting
