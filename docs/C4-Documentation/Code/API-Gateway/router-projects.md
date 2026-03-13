# Projects Router

**Source:** `src/stoat_ferret/api/routers/projects.py`
**Component:** API Gateway

## Purpose

Project CRUD operations and clip management endpoints. Manages project creation, listing, retrieval, deletion, and per-project clip management with validation against source videos.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects | List projects with pagination |
| POST | /api/v1/projects | Create new project |
| GET | /api/v1/projects/{project_id} | Get project by ID |
| DELETE | /api/v1/projects/{project_id} | Delete project |
| GET | /api/v1/projects/{project_id}/clips | List clips in project |
| POST | /api/v1/projects/{project_id}/clips | Add clip to project |
| PATCH | /api/v1/projects/{project_id}/clips/{clip_id} | Update clip |
| DELETE | /api/v1/projects/{project_id}/clips/{clip_id} | Delete clip |

### Functions

- `list_projects(repo: ProjectRepoDep, limit: int=20, offset: int=0) -> ProjectListResponse`: Lists projects with pagination (limit 1-100)

- `create_project(project_data: ProjectCreate, request: Request, repo: ProjectRepoDep) -> ProjectResponse`: Creates new project with output_width, output_height, output_fps. Broadcasts PROJECT_CREATED event. Returns 201 Created.

- `get_project(project_id: str, repo: ProjectRepoDep) -> ProjectResponse`: Gets project by ID. 404 if not found.

- `delete_project(project_id: str, repo: ProjectRepoDep) -> Response`: Deletes project. 204 No Content on success, 404 if not found.

- `list_clips(project_id: str, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> ClipListResponse`: Lists all clips in project. 404 if project not found.

- `add_clip(project_id: str, request: ClipCreate, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep, video_repo: VideoRepoDep) -> ClipResponse`: Adds clip to project. Validates clip against source video using Rust clip.validate(). Returns 201 Created. 404 if project/video not found, 400 if validation fails.

- `update_clip(project_id: str, clip_id: str, request: ClipUpdate, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep, video_repo: VideoRepoDep) -> ClipResponse`: Updates clip in_point, out_point, timeline_position. Revalidates against source video. 404 if project/clip not found, 400 if validation fails.

- `delete_clip(project_id: str, clip_id: str, clip_repo: ClipRepoDep) -> Response`: Deletes clip. 204 No Content on success, 404 if clip not found or doesn't belong to project.

### Dependency Functions

- `get_project_repository(request: Request) -> AsyncProjectRepository`
- `get_clip_repository(request: Request) -> AsyncClipRepository`
- `get_video_repository(request: Request) -> AsyncVideoRepository`

## Key Implementation Details

- **Dependency injection**: Uses type aliases ProjectRepoDep, ClipRepoDep, VideoRepoDep for cleaner signatures
- **Project creation**: Auto-generates project ID and timestamps; accepts output dimensions and frame rate
- **Clip validation**: Uses Rust binding `clip.validate(source_path, source_duration_frames)` to validate in/out points against video duration
- **Clip lifecycle**: Clips must reference existing source video; clip can be updated with new in/out points (revalidated each time)
- **WebSocket broadcasting**: PROJECT_CREATED event broadcast to all connected clients with project ID and name
- **Error handling**: Structured error responses with code and message; clip validation errors return 400 with detailed message
- **Timestamps**: Uses datetime.now(timezone.utc) for creation/update timestamps

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.clip.*`: ClipCreate, ClipListResponse, ClipResponse, ClipUpdate
- `stoat_ferret.api.schemas.project.*`: ProjectCreate, ProjectListResponse, ProjectResponse
- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket manager
- `stoat_ferret.db.async_repository.AsyncVideoRepository`: Video repository
- `stoat_ferret.db.clip_repository.AsyncClipRepository, AsyncSQLiteClipRepository`: Clip persistence
- `stoat_ferret.db.models.Clip, ClipValidationError, Project`: Domain models
- `stoat_ferret.db.project_repository.AsyncProjectRepository, AsyncSQLiteProjectRepository`: Project persistence

### External Dependencies

- `fastapi`: APIRouter, Depends, HTTPException, Query, Request, Response, status
- `datetime.datetime, datetime.timezone`: Timestamps

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Project/clip/video repositories, WebSocket manager
