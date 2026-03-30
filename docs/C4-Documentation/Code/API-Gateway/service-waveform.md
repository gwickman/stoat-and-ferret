# Waveform Service

**Source:** `src/stoat_ferret/api/services/waveform.py`
**Component:** API Gateway

## Purpose

Generates audio waveform visualizations in PNG (image) and JSON (amplitude data) formats using FFmpeg showwavespic and astats filters for timeline audio visualization.

## Public Interface

### Classes

- `WaveformService`: Main service for waveform generation and management
  - `__init__(async_executor, waveform_dir, ffprobe_executor=None, ws_manager=None)`: Initializes service with FFmpeg executor, output directory, optional ffprobe executor, and optional WebSocket manager
  - `get_waveform(video_id: str, fmt: WaveformFormat) -> Waveform | None`: Retrieves waveform metadata from in-memory cache keyed by "{video_id}:{format}"
  - `async generate_png(video_id, video_path, duration_seconds, channels=1, width=1800, height=140, waveform_id=None) -> Waveform`: Generates PNG waveform image via FFmpeg showwavespic
  - `async generate_json(video_id, video_path, duration_seconds, channels=1, waveform_id=None) -> Waveform`: Generates JSON waveform amplitude data via ffprobe astats

### Functions

- `escape_path_for_amovie(path: str) -> str`: Escapes Windows backslashes to forward slashes for FFmpeg amovie filter parameter

- `build_png_ffmpeg_args(video_path, output_path, width=1800, height=140, channels=1) -> list[str]`: Builds FFmpeg arguments for showwavespic filter with channel-specific colors (mono=blue, stereo=blue|red)

- `build_json_ffmpeg_args(video_path) -> list[str]`: Builds ffprobe arguments for amovie+asetnsamples+astats pipeline extracting Peak_level and RMS_level metadata

- `parse_astats_output(raw_output: str) -> list[dict[str, str]]`: Parses ffprobe JSON output extracting Overall and per-channel (ch1, ch2) Peak_level and RMS_level values

### Helper Methods

- `_make_progress_callback(waveform_id, video_id, duration_us) -> callable`: Creates throttled progress callback (>=500ms or >=5% change) for progress info updates

- `_send_progress(waveform_id, video_id, progress, status) -> None`: Sends JOB_PROGRESS WebSocket event with waveform_id, video_id, progress, status

## Key Implementation Details

- **PNG generation**: Uses FFmpeg showwavespic filter with default 1800x140 resolution; automatically selects mono (blue) or stereo (blue|red) color scheme based on channel count

- **JSON generation**: Uses ffprobe with amovie source, asetnsamples (4410 samples = 10 samples/second at 44100 Hz), astats for amplitude extraction; produces 10 samples per second of audio

- **Waveform storage**: In-memory cache dict keyed by "{video_id}:{format.value}" (e.g., "vid-123:png"); survives across multiple calls to same service instance

- **Status lifecycle**: PENDING -> GENERATING -> READY (or ERROR on failure)

- **Path escaping**: Windows backslashes replaced with forward slashes for amovie filter expressions (prevents escaping issues)

- **Progress throttling**: Minimum 500ms between events or 5% change required

- **Error handling**: Catches exceptions, logs detailed error info, updates waveform status to ERROR

- **File output**: PNG files stored as "{waveform_id}.png", JSON files as "{waveform_id}.json" in waveform_dir

- **Metadata tracking**: Records id, video_id, format, status, created_at timestamp, duration, channels, file_path

- **WebSocket broadcasts**: JOB_PROGRESS events during generation with job_type="waveform" for real-time UI updates

- **Timestamp handling**: Uses datetime.now(timezone.utc) for UTC timezone awareness

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder for JOB_PROGRESS
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket manager for broadcasting
- `stoat_ferret.db.models.Waveform, WaveformFormat, WaveformStatus`: Data models and enums (PNG, JSON formats; PENDING, GENERATING, READY, ERROR statuses)
- `stoat_ferret.ffmpeg.async_executor.AsyncFFmpegExecutor, ProgressInfo`: Async FFmpeg/ffprobe execution interface and progress info

### External Dependencies

- `json.loads, json.dumps`: JSON parsing and serialization
- `pathlib.Path`: File system operations (mkdir, write_text, read_text)
- `time.monotonic`: Timing measurements for duration calculation
- `datetime.datetime, datetime.timezone`: Timestamp generation (UTC)
- `structlog`: Structured logging
- `typing.TYPE_CHECKING`: Type hints without runtime overhead

## Constants

- `_PROGRESS_MIN_INTERVAL_S = 0.5`: Minimum 500ms between progress events
- `_PROGRESS_MIN_DELTA = 0.05`: Minimum 5% change between progress events
- `_ASTATS_SAMPLES_PER_SECOND = 4410`: FFmpeg asetnsamples value (44100 Hz / 4410 = 10 samples/s)

## Relationships

- **Used by**: Waveform router (start generation via background tasks), waveform_service dependency in app.state
- **Uses**: Async executor for FFmpeg/ffprobe execution, WebSocket manager for progress broadcasting
- **Stores**: Waveforms in in-memory dict and as files on disk
- **Generates**: JOB_PROGRESS WebSocket events during generation for real-time UI updates
