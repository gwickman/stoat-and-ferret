# Preview Router

**Source:** `src/stoat_ferret/api/routers/preview.py`
**Component:** API Gateway

## Purpose

HLS preview session lifecycle management and media file serving. Provides endpoints to start, monitor, seek within, and stop preview sessions, plus media-type-aware file serving for HLS manifest and segment files.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/preview/cache | Get preview cache status metrics |
| DELETE | /api/v1/preview/cache | Clear all cached preview sessions |
| POST | /api/v1/projects/{project_id}/preview/start | Start new preview session (202 Accepted) |
| GET | /api/v1/preview/{session_id} | Get session status |
| POST | /api/v1/preview/{session_id}/seek | Seek to new position in session |
| DELETE | /api/v1/preview/{session_id} | Stop and clean up session |
| GET | /api/v1/preview/{session_id}/manifest.m3u8 | Serve HLS manifest file |
| GET | /api/v1/preview/{session_id}/segment_{index}.ts | Serve HLS segment file |

### Functions

- `get_cache_status(request: Request) -> PreviewCacheStatusResponse`: Returns cache usage metrics including active session count, byte usage, max bytes, and list of session IDs.

- `clear_cache(request: Request) -> PreviewCacheClearResponse`: Clears all cached sessions and returns count of cleared sessions and bytes freed.

- `start_preview(project_id: str, request: Request, body: PreviewStartRequest | None=None) -> PreviewStartResponse`: Validates project exists and has clips, queues HLS generation. Returns 202 Accepted with session_id. Raises 404 if project not found, 422 if timeline empty, 429 if session limit reached.

- `get_preview_status(session_id: str, request: Request) -> PreviewStatusResponse`: Returns session status and manifest_url when ready. Raises 404 if session not found or expired.

- `seek_preview(session_id: str, body: PreviewSeekRequest, request: Request) -> PreviewSeekResponse`: Triggers segment regeneration from new position. Returns 200 with status "seeking". Raises 404 if session not found.

- `stop_preview(session_id: str, request: Request) -> PreviewStopResponse`: Stops generation, removes segment files, deletes session record. Raises 404 if session not found.

- `get_manifest(session_id: str, request: Request) -> Response`: Serves HLS manifest with Content-Type application/vnd.apple.mpegurl. Raises 404 if session or manifest not found.

- `get_segment(session_id: str, index: int, request: Request) -> Response`: Serves MPEG-TS segment with Content-Type video/MP2T. Raises 404 if session or segment not found.

### Dependency Functions

- `_get_preview_manager(request: Request) -> PreviewManager`: Gets preview manager from app.state or raises 503 SERVICE_UNAVAILABLE.

- `_get_project_repository(request: Request) -> AsyncProjectRepository`: Gets project repository from app.state or creates from app.state.db.

- `_get_clip_repository(request: Request) -> AsyncClipRepository`: Gets clip repository from app.state or creates from app.state.db.

- `_get_preview_cache(request: Request) -> PreviewCache`: Gets preview cache from app.state or raises 503 SERVICE_UNAVAILABLE.

- `_check_ffmpeg_available() -> None`: Checks if ffmpeg is in PATH; raises 503 FFMPEG_UNAVAILABLE if not.

## Key Implementation Details

- **HLS media types**: Manifest served as `application/vnd.apple.mpegurl`, segments as `video/MP2T` (MPEG-TS transport stream format)

- **Quality levels**: Supports "low", "medium", "high"; defaults to "medium" if not specified in request body

- **Segment file naming**: Follows pattern `segment_{index:03d}.ts` (zero-padded 3-digit indices)

- **Manifest location**: Segments stored in same directory as manifest for easy access

- **Session validation**: All session endpoints check for NOT_FOUND and SESSION_EXPIRED states

- **FFmpeg requirement**: start_preview and seek_preview check that ffmpeg is available in PATH

- **Dependency injection**: Uses FastAPI Depends pattern for repositories; creates instances from db connection if not pre-injected (test mode support)

- **Error responses**: JSON:API-style with code/message fields (e.g., `{"code": "NOT_FOUND", "message": "..."}`)

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.preview.*`: All preview request/response models
- `stoat_ferret.api.middleware.correlation`: Get correlation ID for context
- `stoat_ferret.db.clip_repository.AsyncClipRepository, AsyncSQLiteClipRepository`: Clip persistence
- `stoat_ferret.db.models.PreviewQuality`: Quality level enum
- `stoat_ferret.db.project_repository.AsyncProjectRepository, AsyncSQLiteProjectRepository`: Project persistence
- `stoat_ferret.db.async_repository.AsyncVideoRepository`: Video metadata access
- `stoat_ferret.preview.cache.PreviewCache`: Cache status and management
- `stoat_ferret.preview.manager.PreviewManager, SessionExpiredError, SessionLimitError, SessionNotFoundError`: Session lifecycle and error types

### External Dependencies

- `fastapi.APIRouter, HTTPException, Request, Response, status`: Web framework
- `pathlib.Path`: File system operations
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Preview manager and cache for session lifecycle, project/clip/video repositories for validation, FFmpeg availability check
- **Broadcasts**: WebSocket events via preview manager (managed separately)
