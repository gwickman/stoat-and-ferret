---
status: complete
acceptance_passed: 6
acceptance_total: 6
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-thumbnail-pipeline

## Summary

Implemented a thumbnail generation pipeline using the existing FFmpeg executor pattern. The implementation includes a `ThumbnailService` class, a `GET /api/videos/{id}/thumbnail` endpoint with placeholder fallback, and scan integration that generates thumbnails during video scanning.

## Acceptance Criteria

| ID | Criteria | Status |
|----|----------|--------|
| FR-001 | Thumbnail generated for a video file and saved to the configured thumbnail directory | PASS |
| FR-002 | After scanning a directory, all successfully scanned videos have populated `thumbnail_path` | PASS |
| FR-003 | `GET /api/videos/{id}/thumbnail` returns the thumbnail image for a scanned video | PASS |
| FR-004 | Default thumbnail width is 320px with aspect ratio preserved | PASS |
| FR-005 | `GET /api/videos/{id}/thumbnail` returns a placeholder for videos without a thumbnail | PASS |
| FR-006 | Thumbnail generation commands are recorded and can be replayed in tests | PASS |

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/services/thumbnail.py` | Created | ThumbnailService class with `generate()` and `get_thumbnail_path()` |
| `src/stoat_ferret/api/routers/videos.py` | Modified | Added `GET /api/v1/videos/{id}/thumbnail` endpoint |
| `src/stoat_ferret/api/services/scan.py` | Modified | Integrated ThumbnailService into scan_directory flow |
| `src/stoat_ferret/api/app.py` | Modified | Wired ThumbnailService in production lifespan |
| `src/stoat_ferret/static/placeholder-thumb.jpg` | Created | Placeholder JPEG for failed extractions |
| `tests/test_thumbnail_service.py` | Created | 11 unit tests for ThumbnailService |
| `tests/test_api/test_thumbnail_endpoint.py` | Created | 5 integration tests for thumbnail endpoint |

## Test Results

- **Total tests:** 621 passed, 15 skipped
- **Thumbnail unit tests:** 11 passed
- **Thumbnail endpoint tests:** 5 passed
- **Quality gates:** All passing (ruff, ruff format, mypy)

## Design Decisions

1. **Placeholder in package directory**: Placed `placeholder-thumb.jpg` at `src/stoat_ferret/static/` rather than project root `static/` for reliable path resolution relative to the Python package.
2. **Synchronous FFmpeg execution**: `ThumbnailService.generate()` is synchronous, matching the existing `FFmpegExecutor` protocol. The scan service calls it within the async job handler.
3. **Optional thumbnail_service parameter**: `scan_directory()` and `make_scan_handler()` accept an optional `ThumbnailService` to maintain backward compatibility with existing tests and callers.
