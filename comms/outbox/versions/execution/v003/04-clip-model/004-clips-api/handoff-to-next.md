# Handoff: 004-clips-api

## What Was Completed

REST API endpoints for projects and clips are now implemented. Users can:
- Create, list, get, and delete projects
- Add, list, update, and delete clips within projects
- All clip operations validate using Rust core

## Key Implementation Decisions

1. **Video Lookup for Validation**: When creating or updating clips, the source video is fetched from the video repository to get its path and duration for Rust validation.

2. **Dependency Injection Pattern**: Repository access follows the existing pattern from `videos.py`, using FastAPI's `Depends` with functions that create repositories from `request.app.state.db`.

3. **Test Fixtures**: Updated `conftest.py` to provide project and clip in-memory repositories, matching the existing video repository pattern.

## API Endpoints

### Projects
- `GET /api/v1/projects` - List projects (with pagination)
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project by ID
- `DELETE /api/v1/projects/{id}` - Delete project

### Clips
- `GET /api/v1/projects/{id}/clips` - List clips in project
- `POST /api/v1/projects/{id}/clips` - Add clip to project
- `PATCH /api/v1/projects/{id}/clips/{clip_id}` - Update clip
- `DELETE /api/v1/projects/{id}/clips/{clip_id}` - Delete clip

## What the Next Feature Needs to Know

1. **Imports Available**:
   ```python
   from stoat_ferret.api.schemas.project import ProjectCreate, ProjectResponse, ProjectListResponse
   from stoat_ferret.api.schemas.clip import ClipCreate, ClipResponse, ClipListResponse, ClipUpdate
   ```

2. **Router Module**:
   ```python
   from stoat_ferret.api.routers.projects import router
   ```

3. **Dependency Functions** (for testing):
   ```python
   from stoat_ferret.api.routers.projects import (
       get_project_repository,
       get_clip_repository,
       get_video_repository,
   )
   ```

## Integration Points for Next Features

- **Timeline Model**: Will need to aggregate clips with ordering based on `timeline_position`
- **Timeline Export**: Will need to generate FFmpeg commands from project clips
- **Clip Overlap Detection**: API doesn't currently check for overlaps - may need timeline-level validation
- **Project Update Endpoint**: Not implemented (only create/delete) - may need PATCH for name/settings changes
