# Thumbnails Router

**Source:** `src/stoat_ferret/api/routers/thumbnails.py`
**Component:** API Gateway

## Purpose

Thumbnail sprite strip generation and serving. Provides endpoints to queue strip generation, retrieve metadata about generated strips, and serve sprite sheet images as JPEG.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/videos/{video_id}/thumbnails/strip | Queue thumbnail strip generation (202 Accepted) |
| GET | /api/v1/videos/{video_id}/thumbnails/strip | Get thumbnail strip metadata |
| GET | /api/v1/videos/{video_id}/thumbnails/strip.jpg | Serve sprite sheet as JPEG |

### Functions

- `generate_strip(video_id: str, request: Request, background_tasks: BackgroundTasks, video_repo: VideoRepoDep, thumbnail_service: ThumbnailServiceDep, body: ThumbnailStripGenerateRequest | None=None) -> ThumbnailStripGenerateResponse`: Validates video exists, creates strip_id, adds generation task to FastAPI background tasks. Returns 202 Accepted with strip_id and "pending" status. Raises 404 if video not found.

- `get_strip_metadata(video_id: str, thumbnail_service: ThumbnailServiceDep) -> ThumbnailStripMetadataResponse`: Retrieves strip metadata including frame count, dimensions, columns, and rows for sprite layout calculation. Raises 404 if no strip exists for video.

- `get_strip_image(video_id: str, thumbnail_service: ThumbnailServiceDep) -> FileResponse`: Serves the sprite sheet JPEG image. Raises 404 if strip not found or file not ready on disk.

### Dependency Functions

- `_get_video_repository(request: Request) -> AsyncVideoRepository`: Gets video repository from app.state or creates from app.state.db.

- `_get_thumbnail_service(request: Request) -> ThumbnailService`: Gets thumbnail service from app.state or raises 503 SERVICE_UNAVAILABLE.

## Key Implementation Details

- **Background generation**: Uses FastAPI BackgroundTasks to queue thumbnail generation asynchronously without blocking the response

- **Service parameters**: Passes video metadata (id, path, duration_seconds) and optional parameters (interval_seconds, frame_width, frame_height) to service

- **Default dimensions**: Frame width defaults to 160px, height to 90px if not specified in request body

- **Sprite grid layout**: Metadata includes columns and rows so client can calculate frame positions within sprite sheet

- **File serving**: Returns JPEG with media_type="image/jpeg"

- **Service dependency**: ThumbnailService injected from app.state; required for all endpoints (503 if missing)

- **Error responses**: JSON:API-style with code/message fields

- **Dependency injection**: Uses FastAPI Annotated[Type, Depends()] pattern; creates video repo from db if not pre-injected

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.thumbnail.ThumbnailStripGenerateRequest, ThumbnailStripGenerateResponse, ThumbnailStripMetadataResponse`: Request/response schemas
- `stoat_ferret.api.services.thumbnail.ThumbnailService`: Thumbnail generation service with get_strip and generate_strip methods
- `stoat_ferret.db.async_repository.AsyncVideoRepository, AsyncSQLiteVideoRepository`: Video persistence
- `stoat_ferret.db.models.ThumbnailStrip`: Thumbnail strip model with new_id() factory

### External Dependencies

- `fastapi.APIRouter, BackgroundTasks, Depends, HTTPException, Request, status`: Web framework
- `fastapi.responses.FileResponse`: File serving response
- `pathlib.Path`: File system operations
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: ThumbnailService for generation and metadata retrieval, video repository for validation
- **Generates**: Background tasks that call ThumbnailService.generate_strip asynchronously
