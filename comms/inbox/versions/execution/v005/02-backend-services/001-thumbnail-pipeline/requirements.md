# Requirements - 001: Thumbnail Pipeline

## Goal

Implement a thumbnail generation service using the FFmpeg executor pattern, add a `GET /api/videos/{id}/thumbnail` endpoint, and integrate thumbnail generation with the scan service.

## Background

The library browser spec (M1.11) assumes thumbnail display for videos, but no thumbnail generation pipeline exists. Videos are scanned and stored with metadata, but no representative frame is extracted. The `Video` model already has a `thumbnail_path: str | None` field (set to `None` during scan). The FFmpeg executor pattern (Real/Recording/Fake) is established and well-tested (LRN-008).

**Backlog Item:** BL-032

## Functional Requirements

**FR-001: Thumbnail generation service**
Create a `ThumbnailService` that generates thumbnails using the FFmpeg executor. Extract a single frame at the 5-second mark with `scale=320:-1` and JPEG quality 5.
- AC: Thumbnail generated for a video file and saved to the configured thumbnail directory

**FR-002: Scan integration**
Integrate thumbnail generation into the scan service so thumbnails are generated during video scan. Update `Video.thumbnail_path` with the generated thumbnail path.
- AC: After scanning a directory, all successfully scanned videos have populated `thumbnail_path`

**FR-003: Thumbnail API endpoint**
Add `GET /api/videos/{id}/thumbnail` endpoint that returns the thumbnail image with `Content-Type: image/jpeg`.
- AC: `GET /api/videos/{id}/thumbnail` returns the thumbnail image for a scanned video

**FR-004: Configurable thumbnail size**
Thumbnail size defaults to 320px width with auto-calculated height (maintaining aspect ratio). Width configurable via thumbnail service initialization.
- AC: Default thumbnail width is 320px with aspect ratio preserved

**FR-005: Graceful fallback**
Return a placeholder image for videos where thumbnail extraction fails (corrupt file, audio-only, etc.).
- AC: `GET /api/videos/{id}/thumbnail` returns a placeholder for videos without a thumbnail

**FR-006: Recording executor support**
`RecordingFFmpegExecutor` captures thumbnail generation commands for test playback via `FakeFFmpegExecutor`.
- AC: Thumbnail generation commands are recorded and can be replayed in tests

## Non-Functional Requirements

**NFR-001: Thumbnail generation speed**
Single thumbnail extraction completes within 2 seconds for typical video files.
- Metric: FFmpeg thumbnail extraction < 2s per video on local machine

**NFR-002: Storage efficiency**
Thumbnails stored at JPEG quality 5, resulting in approximately 15-30KB per thumbnail.
- Metric: Average thumbnail file size between 10-50KB

## Out of Scope

- Lazy/on-demand thumbnail generation (on-scan only in v005)
- Custom thumbnail selection (always extract at 5-second mark)
- Thumbnail regeneration or cache invalidation
- WebP or other format support

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests | ThumbnailService: generates correct FFmpeg args, stores to configured dir, handles missing video gracefully, returns placeholder on extraction failure |
| Integration tests | `GET /api/videos/{id}/thumbnail` returns image for scanned video; returns placeholder for video without thumbnail; returns 404 for unknown video ID |
| Contract tests | FFmpeg command args match expected pattern via RecordingFFmpegExecutor (LRN-008); thumbnail response Content-Type is `image/jpeg` |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.