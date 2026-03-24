# Phase 4: API Endpoints

## Overview

Phase 4 adds preview, proxy, playback, and visual aid endpoints. All endpoints follow existing REST conventions (see `05-api-specification.md`): nested resources, JSON:API-style errors, and correlation ID middleware.

## Preview Endpoints

### Start Preview Session

Initiates HLS segment generation for a project timeline.

```http
POST /api/v1/projects/{project_id}/preview/start
Content-Type: application/json

{
  "quality": "720p",
  "start_position": 0.0,
  "segment_duration": 4.0
}

Response 202:
{
  "session_id": "prev_abc123",
  "project_id": "proj_001",
  "status": "initializing",
  "quality": "720p",
  "estimated_segments": 12,
  "message": "Preview generation started"
}
```

Quality is optional - auto-selected based on timeline complexity if omitted. Returns 202 Accepted (async job). WebSocket broadcasts `preview.generating` and `preview.ready` events.

### Get Preview Status

```http
GET /api/v1/preview/{session_id}

Response 200:
{
  "session_id": "prev_abc123",
  "project_id": "proj_001",
  "status": "ready",
  "quality": "720p",
  "manifest_url": "/api/v1/preview/prev_abc123/manifest.m3u8",
  "duration": 45.5,
  "segments_generated": 12,
  "segments_total": 12,
  "expires_at": "2026-03-24T15:00:00Z"
}
```

### Serve HLS Manifest

```http
GET /api/v1/preview/{session_id}/manifest.m3u8

Response 200 (Content-Type: application/vnd.apple.mpegurl):
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:4
...
#EXT-X-ENDLIST
```

### Serve HLS Segment

```http
GET /api/v1/preview/{session_id}/segment_{index}.ts

Response 200 (Content-Type: video/mp2t):
[binary MPEG-TS data]
```

### Seek Preview

Regenerates segments from a new position. Returns updated manifest.

```http
POST /api/v1/preview/{session_id}/seek
Content-Type: application/json

{
  "position": 15.5
}

Response 200:
{
  "session_id": "prev_abc123",
  "status": "seeking",
  "seek_position": 15.5,
  "message": "Regenerating segments from position 15.5s"
}
```

WebSocket broadcasts `preview.seeking` then `preview.ready` when segments are available.

### Stop Preview Session

```http
DELETE /api/v1/preview/{session_id}

Response 200:
{
  "session_id": "prev_abc123",
  "status": "expired",
  "message": "Preview session stopped, segments cleaned up"
}
```

## Proxy Management Endpoints

### Generate Proxy for Video

```http
POST /api/v1/videos/{video_id}/proxy
Content-Type: application/json

{
  "quality": "720p"
}

Response 202:
{
  "proxy_id": "proxy_xyz789",
  "video_id": 1,
  "quality": "720p",
  "status": "pending",
  "job_id": "job_proxy_001"
}
```

Quality is optional - auto-selected based on source resolution.

### Get Proxy Status

```http
GET /api/v1/videos/{video_id}/proxy

Response 200:
{
  "proxy_id": "proxy_xyz789",
  "video_id": 1,
  "quality": "720p",
  "status": "ready",
  "file_size_bytes": 52428800,
  "generated_at": "2026-03-24T12:00:00Z"
}
```

### Batch Generate Proxies

Triggered automatically during scan (if `proxy_auto_generate` enabled) or manually.

```http
POST /api/v1/proxy/batch
Content-Type: application/json

{
  "video_ids": [1, 2, 3, 5],
  "quality": "720p"
}

Response 202:
{
  "batch_id": "proxy_batch_001",
  "total": 4,
  "queued": 4,
  "skipped": 0,
  "message": "Proxy generation queued for 4 videos"
}
```

Videos with existing ready proxies at the requested quality are skipped.

### Delete Proxy

```http
DELETE /api/v1/videos/{video_id}/proxy

Response 200:
{
  "video_id": 1,
  "deleted": true,
  "freed_bytes": 52428800
}
```

## Thumbnail Strip Endpoints

### Generate Thumbnail Strip

```http
POST /api/v1/videos/{video_id}/thumbnails/strip
Content-Type: application/json

{
  "interval_seconds": 5.0,
  "frame_width": 160,
  "frame_height": 90
}

Response 202:
{
  "video_id": 1,
  "status": "generating",
  "job_id": "job_strip_001",
  "estimated_frames": 60
}
```

### Get Thumbnail Strip

```http
GET /api/v1/videos/{video_id}/thumbnails/strip

Response 200:
{
  "video_id": 1,
  "strip_url": "/api/v1/videos/1/thumbnails/strip.jpg",
  "frame_count": 60,
  "frame_width": 160,
  "frame_height": 90,
  "interval_seconds": 5.0,
  "total_duration": 300.0
}
```

### Serve Thumbnail Strip Image

```http
GET /api/v1/videos/{video_id}/thumbnails/strip.jpg

Response 200 (Content-Type: image/jpeg):
[binary JPEG data - horizontal sprite sheet]
```

## Waveform Endpoints

### Generate Waveform

```http
POST /api/v1/videos/{video_id}/waveform
Content-Type: application/json

{
  "format": "png",
  "width": 1920,
  "height": 120
}

Response 202:
{
  "video_id": 1,
  "format": "png",
  "status": "generating",
  "job_id": "job_wave_001"
}
```

### Get Waveform

```http
GET /api/v1/videos/{video_id}/waveform?format=png

Response 200:
{
  "video_id": 1,
  "format": "png",
  "waveform_url": "/api/v1/videos/1/waveform.png",
  "duration": 300.0,
  "channels": 2,
  "samples_per_second": 10
}
```

### Serve Waveform Image

```http
GET /api/v1/videos/{video_id}/waveform.png

Response 200 (Content-Type: image/png):
[binary PNG data - waveform visualization]
```

## Preview Cache Endpoints

### Get Cache Status

```http
GET /api/v1/preview/cache

Response 200:
{
  "active_sessions": 2,
  "max_sessions": 5,
  "used_bytes": 524288000,
  "max_bytes": 1073741824,
  "usage_percent": 48.8,
  "sessions": [
    {
      "session_id": "prev_abc123",
      "project_id": "proj_001",
      "size_bytes": 262144000,
      "created_at": "2026-03-24T12:00:00Z",
      "last_accessed": "2026-03-24T12:30:00Z"
    }
  ]
}
```

### Clear Preview Cache

```http
DELETE /api/v1/preview/cache

Response 200:
{
  "cleared_sessions": 2,
  "freed_bytes": 524288000,
  "message": "Preview cache cleared"
}
```

## WebSocket Events (Phase 4 Additions)

All events broadcast on existing `/ws` WebSocket endpoint.

### Preview Events

```json
{
  "type": "preview.generating",
  "session_id": "prev_abc123",
  "project_id": "proj_001",
  "progress": 0.45,
  "segments_generated": 5,
  "segments_total": 12,
  "timestamp": "2026-03-24T12:00:05Z"
}

{
  "type": "preview.ready",
  "session_id": "prev_abc123",
  "project_id": "proj_001",
  "manifest_url": "/api/v1/preview/prev_abc123/manifest.m3u8",
  "duration": 45.5,
  "quality": "720p",
  "timestamp": "2026-03-24T12:00:15Z"
}

{
  "type": "preview.seeking",
  "session_id": "prev_abc123",
  "seek_position": 15.5,
  "timestamp": "2026-03-24T12:00:20Z"
}

{
  "type": "preview.error",
  "session_id": "prev_abc123",
  "error_code": "FFMPEG_ERROR",
  "message": "FFmpeg exited with code 1",
  "timestamp": "2026-03-24T12:00:25Z"
}
```

### Proxy Events

```json
{
  "type": "proxy.generating",
  "video_id": 1,
  "quality": "720p",
  "progress": 0.65,
  "timestamp": "2026-03-24T12:01:00Z"
}

{
  "type": "proxy.ready",
  "video_id": 1,
  "quality": "720p",
  "file_size_bytes": 52428800,
  "timestamp": "2026-03-24T12:02:00Z"
}
```

### AI Theater Mode Events

```json
{
  "type": "ai_action",
  "action": "applying_effect",
  "target": "clip_003",
  "description": "Adding text overlay 'Chapter 1' with fade-in",
  "timestamp": "2026-03-24T12:05:00Z"
}

{
  "type": "render_progress",
  "job_id": "job_render_001",
  "progress": 0.45,
  "current_frame": 1350,
  "total_frames": 3000,
  "eta_seconds": 120,
  "current_operation": "encoding_frame",
  "timestamp": "2026-03-24T12:06:00Z"
}
```

## Error Cases

All endpoints return structured errors per existing pattern:

```json
{
  "error": {
    "code": "PREVIEW_SESSION_NOT_FOUND",
    "category": "not_found",
    "message": "Preview session prev_xyz789 does not exist or has expired",
    "suggestion": "Start a new preview session with POST /projects/{id}/preview/start",
    "correlation_id": "req_abc123"
  }
}
```

| Error Code | HTTP Status | Condition |
|-----------|------------|-----------|
| `PREVIEW_SESSION_NOT_FOUND` | 404 | Session ID doesn't exist or expired |
| `PREVIEW_SESSION_EXPIRED` | 410 | Session timed out, segments cleaned up |
| `PREVIEW_ALREADY_ACTIVE` | 409 | Project already has an active preview session |
| `PROXY_ALREADY_EXISTS` | 409 | Proxy at requested quality already exists for video |
| `PROXY_NOT_FOUND` | 404 | No proxy exists for video |
| `VIDEO_NOT_FOUND` | 404 | Referenced video doesn't exist |
| `EMPTY_TIMELINE` | 422 | Cannot preview a project with no clips |
| `FFMPEG_UNAVAILABLE` | 503 | FFmpeg binary not found or not responsive |
| `PREVIEW_CACHE_FULL` | 507 | Cache at capacity, eviction failed |
| `THUMBNAIL_GENERATION_FAILED` | 500 | FFmpeg failed to generate thumbnail strip |
| `WAVEFORM_GENERATION_FAILED` | 500 | FFmpeg failed to generate waveform |
| `INVALID_SEEK_POSITION` | 422 | Seek position outside timeline range |

## New Router Files

```
src/stoat_ferret/api/routers/
├── preview.py        # NEW - preview session management, HLS serving
├── proxy.py          # NEW - proxy file management
├── thumbnails.py     # NEW - thumbnail strip generation and serving
├── waveform.py       # NEW - waveform generation and serving
├── timeline.py       # existing (no changes)
├── compose.py        # existing (no changes)
├── audio.py          # existing (no changes)
├── batch.py          # existing (no changes)
├── versions.py       # existing (no changes)
├── projects.py       # existing (no changes)
├── effects.py        # existing (no changes)
├── videos.py         # EXTEND - proxy status on video responses
├── jobs.py           # existing (no changes)
├── health.py         # EXTEND - preview subsystem health check
└── ...
```
