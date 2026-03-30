# Proxy Service

**Source:** `src/stoat_ferret/api/services/proxy_service.py`
**Component:** API Gateway

## Purpose

Orchestrates proxy video file generation with FFmpeg transcoding, storage quota management, LRU cache eviction, stale proxy detection, and WebSocket progress broadcasting.

## Public Interface

### Classes

- `ProxyService`: Main service for proxy generation and management
  - `__init__(proxy_repository, async_executor, ws_manager=None, job_queue=None, proxy_dir="proxies", max_storage_bytes=10GB, cleanup_threshold=0.80)`: Initializes service with dependency injection
  - `async generate_proxy(video_id, source_path, source_width, source_height, duration_us, job_id=None, cancel_event=None) -> ProxyFile`: Generates proxy with quality selection, quota checking, FFmpeg execution, metrics recording, and WebSocket broadcast
  - `async check_stale(proxy_id, source_path) -> bool`: Compares source checksums; marks proxy STALE if source changed

### Functions

- `select_proxy_quality(source_width: int, source_height: int) -> tuple[ProxyQuality, int, int]`: Selects quality level and target resolution based on source height thresholds (>1080p=HIGH 1280x720, >720p=MEDIUM 960x540, <=720p=LOW passthrough)

- `build_ffmpeg_args(source_path, output_path, target_width, target_height) -> list[str]`: Builds FFmpeg command arguments for H.264 transcoding with scale filter, fast preset, CRF 23, AAC audio 128k, and progress reporting to pipe:2

- `compute_file_checksum(file_path, chunk_size=8192) -> str`: Computes SHA-256 hex digest in 8KB chunks

- `make_proxy_handler(proxy_service) -> callable`: Factory creating async job handler for AsyncioJobQueue with signature (job_type, payload) -> dict[str, Any]

- `_remove_file_if_exists(path)`: Silently removes file if it exists

- `_run_in_thread(fn, *args)`: Runs blocking function in thread pool via asyncio.to_thread

### Helper Functions

- `_check_quota_and_evict() -> None`: Checks storage usage against threshold (80% by default); evicts LRU proxies via last_accessed_at timestamp until below threshold

- `_make_progress_callback(job_id, video_id, quality, target_resolution, duration_us) -> callable`: Creates throttled progress callback (>=500ms or >=5% change between events) for ProgressInfo updates

- `_send_progress(job_id, progress, status, quality, target_resolution) -> None`: Sends JOB_PROGRESS WebSocket event and updates job queue progress

## Key Implementation Details

- **Quality selection**: Three-tier system based on source height with different target resolutions; <=720p uses passthrough (no transcoding)

- **FFmpeg presets**: Uses "fast" preset (-preset fast) for reasonable quality/speed tradeoff; CRF 23 for acceptable visual quality

- **Quota management**: Max 10GB storage by default; cleanup threshold 80% triggers LRU eviction of oldest-accessed proxies

- **Storage metrics**: Tracks proxy_files_total (by status: pending, ready, failed), proxy_storage_bytes (total bytes), proxy_generation_seconds (by quality), proxy_evictions_total (by reason)

- **Status lifecycle**: PENDING -> GENERATING -> READY (or FAILED/CANCELLED on error)

- **Checksum tracking**: Stores source_checksum on ProxyFile; check_stale() compares current checksum with stored value to detect source changes

- **Progress throttling**: Minimum 500ms between progress events or 5% change required to avoid flooding WebSocket with updates

- **Error handling**: Cleans up partial files on FFmpeg failure or cancellation; transitions to FAILED status; logs detailed error info

- **Job handler**: Returns dict with proxy_id, quality, file_path for caller to access generated proxy

- **WebSocket broadcasts**: PROXY_READY event on successful completion; JOB_PROGRESS events during generation for real-time UI updates

- **Thread safety**: Uses asyncio.to_thread for blocking file operations (checksum, file removal)

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder for PROXY_READY, JOB_PROGRESS
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket manager for broadcasting
- `stoat_ferret.db.models.ProxyFile, ProxyQuality, ProxyStatus`: Data models and enums
- `stoat_ferret.db.proxy_repository.AsyncProxyRepository`: Proxy persistence interface
- `stoat_ferret.ffmpeg.async_executor.AsyncFFmpegExecutor, ProgressInfo`: Async FFmpeg execution and progress info
- `stoat_ferret.jobs.queue.AsyncJobQueue`: Job queue for progress tracking
- `stoat_ferret.preview.metrics`: Prometheus metrics (proxy_files_total, proxy_storage_bytes, proxy_generation_seconds, proxy_evictions_total)

### External Dependencies

- `asyncio.Event`: Cancellation signaling
- `hashlib.sha256`: Checksum computation
- `pathlib.Path`: File system operations
- `time.monotonic`: Timing measurements
- `datetime.datetime, datetime.timezone`: Timestamp generation
- `structlog`: Structured logging
- `os.path.exists, os.remove`: File operations

## Constants

- `PROXY_JOB_TYPE = "proxy"`: Job type identifier for queue
- `DEFAULT_MAX_STORAGE_BYTES = 10 * 1024 * 1024 * 1024`: 10 GB default quota
- `CLEANUP_THRESHOLD = 0.80`: 80% triggers eviction
- `PROGRESS_MIN_INTERVAL_S = 0.5`: Minimum 500ms between progress events
- `PROGRESS_MIN_DELTA = 0.05`: Minimum 5% change between progress events

## Relationships

- **Used by**: Proxy router (generates via job submission), job queue (executes via make_proxy_handler)
- **Uses**: Proxy repository for persistence, async executor for FFmpeg, WebSocket manager for broadcasting, job queue for progress tracking
- **Generates**: PROXY_READY and JOB_PROGRESS WebSocket events for real-time UI updates
