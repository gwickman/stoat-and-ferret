# Thumbnail Service

**Source:** `src/stoat_ferret/api/services/thumbnail.py`
**Component:** API Gateway

## Purpose

Video thumbnail generation service using FFmpeg. Extracts a single frame at a configurable time offset, scales to specified width, and saves as JPEG.

## Public Interface

### Classes

- `ThumbnailService`: Generates video thumbnails using FFmpeg executor.
  - `__init__(executor: FFmpegExecutor, thumbnail_dir: str | Path, *, width: int=320) -> None`: Initializes service with FFmpeg executor, thumbnail output directory, and optional width (default 320px)
  - `generate(video_path: str, video_id: str) -> str | None`: Generates thumbnail for video. Returns path to generated file or None on failure.
  - `get_thumbnail_path(video_id: str) -> str | None`: Checks if thumbnail file exists for video. Returns path or None.

## Key Implementation Details

- **Frame extraction**: Extracts single frame at 5-second offset via `-ss 5 -frames:v 1`

- **Scaling**: Scales to configured width with `-1` for height (maintains aspect ratio)

- **JPEG quality**: Set to quality level 5 (on 0-31 scale, lower is better) via `-q:v 5`

- **Timeout**: 30-second timeout to prevent hanging on problematic videos

- **File naming**: Thumbnail saved as `{thumbnail_dir}/{video_id}.jpg`

- **Error handling**: Catches exceptions and logs warnings; returns None on failure to allow scan to continue

- **Return code checking**: Validates FFmpeg exit code; logs failure if non-zero

- **Directory creation**: Creates thumbnail directory with parents if needed via mkdir(parents=True, exist_ok=True)

- **Logging**: Logs thumbnail generation success with output path and execution duration; logs warnings on error/failure

## Dependencies

### Internal Dependencies

- `stoat_ferret.ffmpeg.executor.FFmpegExecutor`: FFmpeg execution interface

### External Dependencies

- `pathlib.Path`: Path operations
- `structlog`: Structured logging

## Relationships

- **Used by**: `app.py` (created in lifespan), scan service (called during directory scanning)
- **Uses**: FFmpeg executor for frame extraction
