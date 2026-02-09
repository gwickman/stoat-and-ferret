# Implementation Plan - 001: Thumbnail Pipeline

## Overview

Implement a `ThumbnailService` that generates thumbnails using the existing FFmpeg executor pattern, add a `GET /api/videos/{id}/thumbnail` endpoint, and integrate thumbnail generation into the scan service. The `Video.thumbnail_path` field already exists on the model.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/services/thumbnail.py` | Create | ThumbnailService class using FFmpeg executor |
| `src/stoat_ferret/api/routers/videos.py` | Modify | Add `GET /api/videos/{id}/thumbnail` endpoint |
| `src/stoat_ferret/api/services/scan.py` | Modify | Integrate thumbnail generation into scan flow |
| `src/stoat_ferret/api/app.py` | Modify | Wire ThumbnailService in lifespan/DI |
| `tests/test_thumbnail_service.py` | Create | ThumbnailService unit tests |
| `tests/test_thumbnail_endpoint.py` | Create | Thumbnail endpoint integration tests |
| `static/placeholder-thumb.jpg` | Create | Placeholder thumbnail for failed extractions |

## Implementation Stages

### Stage 1: ThumbnailService

1. Create `ThumbnailService` class accepting FFmpeg executor and thumbnail directory path
2. Implement `generate(video_path: str, video_id: str) -> str | None`:
   - Build FFmpeg args: `["-ss", "5", "-i", video_path, "-frames:v", "1", "-vf", "scale=320:-1", "-q:v", "5", "-y", output_path]`
   - Execute via FFmpeg executor
   - Return output path on success, `None` on failure
3. Implement `get_thumbnail_path(video_id: str) -> str | None`: check if thumbnail file exists
4. Ensure `RecordingFFmpegExecutor` captures thumbnail commands

**Verification:**
```bash
uv run pytest tests/test_thumbnail_service.py -v
```

### Stage 2: Thumbnail API Endpoint

1. Add `GET /api/videos/{id}/thumbnail` to videos router
2. Look up video, check `thumbnail_path`
3. Return `FileResponse` with `media_type="image/jpeg"` if thumbnail exists
4. Return placeholder image if thumbnail doesn't exist
5. Return 404 if video ID not found

**Verification:**
```bash
uv run pytest tests/test_thumbnail_endpoint.py -v
```

### Stage 3: Scan Integration

1. Modify `scan_directory()` in scan service to call `ThumbnailService.generate()` after successful probe
2. Update `Video.thumbnail_path` with the generated path
3. Save updated video record via repository

**Verification:**
```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/
```

## Test Infrastructure Updates

- `FakeFFmpegExecutor` handles thumbnail generation commands (replay from recordings)
- Placeholder image included as static asset for fallback tests
- Integration tests use `RecordingFFmpegExecutor` to verify FFmpeg args

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- **R-4 (Thumbnail performance):** On-scan generation adds 1-2s per video to async scan job. Acceptable for v005 library sizes. See risk assessment.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: add thumbnail generation pipeline with API endpoint

- Implement ThumbnailService using FFmpeg executor pattern
- Add GET /api/videos/{id}/thumbnail endpoint with placeholder fallback
- Integrate thumbnail generation into scan service
- Add unit and integration tests with recording executor

Implements BL-032
```