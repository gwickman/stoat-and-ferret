---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 003-videos-scan

## Summary

Implemented the `POST /api/v1/videos/scan` endpoint for scanning directories to discover and catalog video files. The endpoint walks a specified directory (optionally recursively), filters for video file extensions, extracts metadata using FFprobe, and stores/updates video entries in the repository.

## Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| Scans directory for video files | PASS | Implemented directory walking with glob patterns, filtering by video extensions (.mp4, .mkv, .avi, .mov, .webm, .m4v) |
| Uses FFprobe to extract metadata | PASS | Integrates with existing `ffprobe_video` function to extract duration, dimensions, codecs, and frame rate |
| Returns scan summary | PASS | Response includes scanned, new, updated, skipped counts and error list |
| Handles errors gracefully | PASS | Individual file failures are captured in errors list; scan continues processing remaining files |

## Changes Made

### New Files

1. **`src/stoat_ferret/api/services/scan.py`**
   - `VIDEO_EXTENSIONS` constant defining supported video file extensions
   - `scan_directory()` async function implementing the core scanning logic

### Modified Files

1. **`src/stoat_ferret/api/schemas/video.py`**
   - Added `ScanRequest` schema with `path` and `recursive` fields
   - Added `ScanError` schema for individual file errors
   - Added `ScanResponse` schema with scan result counts and errors

2. **`src/stoat_ferret/api/routers/videos.py`**
   - Added `POST /scan` endpoint calling the scan service
   - Returns 400 with `INVALID_PATH` error code for invalid directories

3. **`tests/test_api/test_videos.py`**
   - Added 9 new tests for scan endpoint functionality
   - Tests cover: invalid paths, empty directories, finding videos, recursive/non-recursive scanning, updating existing videos, error handling

## Test Results

- All 313 tests passed
- 8 tests skipped (FFmpeg-dependent tests in environments without FFmpeg)
- Coverage: 92.44% (exceeds 80% threshold)

## API Response Format

```json
{
  "scanned": 47,
  "new": 12,
  "updated": 3,
  "skipped": 32,
  "errors": [
    {"path": "/path/to/failed.mp4", "error": "Probe failed: ..."}
  ]
}
```
