# Videos Router

**Source:** `src/stoat_ferret/api/routers/videos.py`
**Component:** API Gateway

## Purpose

Video listing, search, retrieval, thumbnail serving, directory scanning, and deletion endpoints. Manages the library of scanned video files with metadata and optional thumbnail images.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/videos | List videos with pagination |
| GET | /api/v1/videos/search | Search videos by filename or path |
| GET | /api/v1/videos/{video_id} | Get video by ID |
| GET | /api/v1/videos/{video_id}/thumbnail | Get video thumbnail (JPEG) |
| POST | /api/v1/videos/scan | Submit directory scan as async job |
| DELETE | /api/v1/videos/{video_id} | Delete video from library |

### Functions

- `list_videos(repo: RepoDep, limit: int=20, offset: int=0) -> VideoListResponse`: Lists videos with pagination (limit 1-100, offset >= 0)

- `search_videos(repo: RepoDep, q: str, limit: int=20) -> VideoSearchResponse`: Searches videos by query string with limit 1-100

- `get_video(video_id: str, repo: RepoDep) -> VideoResponse`: Returns single video by ID. 404 if not found.

- `get_thumbnail(video_id: str, repo: RepoDep) -> FileResponse`: Returns JPEG thumbnail. Falls back to placeholder if thumbnail missing or not generated. 404 if video not found.

- `scan_videos(scan_request: ScanRequest, request: Request) -> JobSubmitResponse`: Submits scan job (returns 202 Accepted with job_id immediately). Validates path is directory and within allowed_scan_roots. 400 if invalid path, 403 if outside allowed roots.

- `delete_video(video_id: str, repo: RepoDep, delete_file: bool=False) -> Response`: Deletes video from library. Optionally deletes source file from disk (if delete_file=True). 204 No Content on success, 404 if not found.

- `get_repository(request: Request) -> AsyncVideoRepository`: Dependency function that returns injected repository or constructs SQLiteVideoRepository from app.state.db

## Key Implementation Details

- **Dependency injection**: Uses Annotated[AsyncVideoRepository, Depends(get_repository)] type alias for cleaner signatures
- **Pagination**: limit clamped to 1-100, offset must be >= 0
- **Search**: Full-text search support via repository.search()
- **Thumbnail fallback**: Uses placeholder image (_PLACEHOLDER_PATH) if no thumbnail exists or on generation failure
- **Scan validation**: Validates directory exists, is readable, and falls within allowed_scan_roots (security)
- **Scan is async**: Returns 202 Accepted immediately with job_id; client polls /api/v1/jobs/{job_id} for status
- **File deletion**: Optional delete_file query param silently ignores OSError on file delete (contextlib.suppress)
- **Error handling**: All 404s use structured error responses with code and message

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.video.*`: VideoListResponse, VideoResponse, VideoSearchResponse, ScanRequest
- `stoat_ferret.api.schemas.job.JobSubmitResponse`: Job submission response
- `stoat_ferret.api.services.scan.SCAN_JOB_TYPE, validate_scan_path`: Scan job type and path validation
- `stoat_ferret.api.settings.get_settings`: Settings for allowed_scan_roots
- `stoat_ferret.db.async_repository.AsyncVideoRepository, AsyncSQLiteVideoRepository`: Video persistence

### External Dependencies

- `fastapi`: APIRouter, Depends, HTTPException, Query, Request, Response, FileResponse, status

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Video repository, job queue (via app.state), scan service
