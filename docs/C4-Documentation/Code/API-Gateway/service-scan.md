# Scan Service

**Source:** `src/stoat_ferret/api/services/scan.py`
**Component:** API Gateway

## Purpose

Directory scanning service for video file discovery. Recursively walks directories, probes video metadata via ffprobe, generates thumbnails, and persists videos to repository with progress tracking and cancellation support.

## Public Interface

### Constants

- `VIDEO_EXTENSIONS`: Set of supported video extensions {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
- `SCAN_JOB_TYPE`: String identifier "scan" for job queue

### Functions

- `validate_scan_path(path: str, allowed_roots: list[str]) -> str | None`: Validates scan path falls under allowed root directories. Returns error message if path not allowed, None if valid. Empty allowed_roots list allows all paths.

- `make_scan_handler(repository: AsyncVideoRepository, thumbnail_service: ThumbnailService | None=None, ws_manager: ConnectionManager | None=None, queue: AsyncJobQueue | None=None) -> Callable[[str, dict[str, Any]], Awaitable[Any]]`: Creates a scan job handler bound to a repository. Returns async handler compatible with job queue.

- `scan_directory(path: str, recursive: bool, repository: AsyncVideoRepository, thumbnail_service: ThumbnailService | None=None, *, progress_callback: Callable[[float], None] | None=None, cancel_event: asyncio.Event | None=None) -> ScanResponse`: Scans directory for videos. Walks path (optionally recursively), probes each video file, generates thumbnails if service available, adds/updates in repository. Returns ScanResponse with counts. Raises ValueError if path not valid directory.

## Key Implementation Details

- **Handler factory**: make_scan_handler() creates closure over repository/services; handler signature matches job queue interface (job_type, payload) -> result

- **Payload structure**: Scan payload contains:
  - `path`: Directory to scan
  - `recursive`: Whether to recurse (default True)
  - `_job_id`: Job ID for progress reporting (injected by queue)
  - `_cancel_event`: Cancellation event (injected by queue)

- **Progress tracking**: If job_id and queue provided, progress_callback updates queue.set_progress() after each file; value is 0.0-1.0

- **Cancellation**: Checks cancel_event.is_set() before processing each file; breaks early on cancellation

- **Video detection**: Uses suffix matching against VIDEO_EXTENSIONS (case-insensitive)

- **Metadata extraction**: Calls ffprobe_video() for each file to get duration_frames, frame_rate, dimensions, codecs

- **Thumbnail generation**: Calls thumbnail_service.generate() if available; captures error and continues (thumbnail optional)

- **Update vs. insert**: Checks if video already exists by path; updates if exists, inserts if new

- **WebSocket events**: Broadcasts SCAN_STARTED with path and SCAN_COMPLETED with path and video_count to ws_manager if available

- **Result counts**: Returns ScanResponse with scanned (total processed), new (inserted), updated (changed), skipped (unchanged), errors (failures)

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.video.ScanError, ScanResponse`: Scan result schemas
- `stoat_ferret.api.services.thumbnail.ThumbnailService`: Thumbnail generation
- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket broadcasting
- `stoat_ferret.db.async_repository.AsyncVideoRepository`: Video persistence
- `stoat_ferret.db.models.Video`: Video domain model
- `stoat_ferret.ffmpeg.probe.ffprobe_video`: FFmpeg metadata extraction
- `stoat_ferret.jobs.queue.AsyncJobQueue`: Job queue for progress

### External Dependencies

- `asyncio.Event`: Cancellation event
- `pathlib.Path`: Path operations
- `structlog`: Structured logging

## Relationships

- **Used by**: `app.py` (job handler registration), videos router (scan endpoint)
- **Uses**: Video repository, ffprobe, thumbnail service, WebSocket manager, job queue
