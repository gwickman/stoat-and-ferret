# THEME_DESIGN - 02: Backend Services

## Goal

Add backend capabilities that the GUI components consume: thumbnail generation pipeline and pagination total count fix. These are backend-only changes that must land before the GUI panels that depend on them.

## Backlog Items

BL-032, BL-034

## Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 001 | thumbnail-pipeline | Thumbnail generation via FFmpeg executor, API endpoint, scan integration | BL-032 | Theme 01 complete (settings fields) |
| 002 | pagination-total-count | Add count() to repository protocol, fix list/search total | BL-034 | None (independent) |

## Dependencies

- **Inbound:** Theme 01 Feature 003 provides `thumbnail_dir` settings field.
- **Outbound:** Theme 03 Feature 003 (library browser) depends on both features.

## Technical Approach

- **Thumbnail pipeline:** New `ThumbnailService` class using `RealFFmpegExecutor` (LRN-008 record-replay pattern). FFmpeg args: `-ss 5 -i <path> -frames:v 1 -vf scale=320:-1 -q:v 5 <output>`. Thumbnails stored in `data/thumbnails/` (configurable via `STOAT_THUMBNAIL_DIR`). New `GET /api/videos/{id}/thumbnail` endpoint returns image/jpeg. Scan service updated to generate thumbnails on scan. Graceful fallback returns placeholder for failed extractions. `Video.thumbnail_path` field already exists on model.
- **Pagination fix:** Add `count()` method to `AsyncVideoRepository` protocol. Implement in `AsyncSQLiteVideoRepository` (via `SELECT COUNT(*)`) and `AsyncInMemoryVideoRepository` (via `len()`). Update `list_videos` and `search` router endpoints to call `count()` and return true total instead of `len(videos)`.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R-4: Thumbnail generation performance | Medium | On-scan generation; scan is async job, latency added to background task not API |

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md` for details.