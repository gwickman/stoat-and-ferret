# Phase 5: API Endpoints

## Overview

Phase 5 adds render job management, output format selection, hardware encoder status, and render queue management endpoints. All endpoints follow existing REST conventions (see `05-api-specification.md`): nested resources, JSON:API-style errors, and correlation ID middleware. Render jobs use the WebSocket push pattern established in Phase 4 (BL-141) for progress updates.

## Render Endpoints

### Start Render

Initiates a render job for a project timeline.

```http
POST /api/v1/projects/{project_id}/render
Content-Type: application/json

{
  "output_format": "mp4",
  "quality_preset": "high",
  "output_path": "/home/user/output/my_video.mp4",
  "width": 1920,
  "height": 1080,
  "fps": 30.0,
  "two_pass": true
}

Response 202:
{
  "job_id": "render_abc123",
  "project_id": "proj_001",
  "status": "pending",
  "output_format": "mp4",
  "quality_preset": "high",
  "encoder": "libx264",
  "hardware_accelerated": false,
  "estimated_frames": 9000,
  "estimated_duration_seconds": 300.0,
  "estimated_file_size_bytes": 375000000,
  "message": "Render job queued"
}
```

All fields except `project_id` are optional — defaults from Settings are used. When `quality_preset` is `"high"`, `two_pass` defaults to `true` (configurable via `SF_RENDER_TWO_PASS_DEFAULT`). Returns 202 Accepted (async job). WebSocket broadcasts `render.started`, `render.progress`, and `render.completed` events.

**Pre-flight checks** (performed synchronously before queuing):
1. Timeline not empty (422 `EMPTY_TIMELINE`)
2. Output directory writable (422 `OUTPUT_DIR_NOT_WRITABLE`)
3. Sufficient disk space per `estimate_output_size()` (507 `INSUFFICIENT_DISK_SPACE`)
4. Queue not full (429 `RENDER_QUEUE_FULL`)
5. Render settings valid per `validate_render_settings()` (422 with details)

### Get Render Status

```http
GET /api/v1/render/{job_id}

Response 200:
{
  "job_id": "render_abc123",
  "project_id": "proj_001",
  "status": "rendering",
  "output_format": "mp4",
  "quality_preset": "high",
  "encoder": "h264_nvenc",
  "hardware_accelerated": true,
  "progress": 0.45,
  "current_frame": 4050,
  "total_frames": 9000,
  "fps": 145.2,
  "eta_seconds": 34,
  "elapsed_seconds": 28,
  "output_path": "/home/user/output/my_video.mp4",
  "output_width": 1920,
  "output_height": 1080,
  "two_pass": false,
  "created_at": "2026-03-24T12:00:00Z",
  "started_at": "2026-03-24T12:00:02Z"
}
```

### Cancel Render

```http
POST /api/v1/render/{job_id}/cancel

Response 200:
{
  "job_id": "render_abc123",
  "status": "cancelled",
  "elapsed_seconds": 28.5,
  "progress_at_cancel": 0.45,
  "temp_files_cleaned": true,
  "message": "Render cancelled and temporary files cleaned up"
}
```

Cancellation sends SIGTERM to the FFmpeg process, waits up to 5 seconds for graceful exit, then SIGKILL. Temporary files are cleaned up.

### List Render Jobs

```http
GET /api/v1/render?status=rendering&limit=10

Response 200:
{
  "jobs": [
    {
      "job_id": "render_abc123",
      "project_id": "proj_001",
      "status": "rendering",
      "progress": 0.45,
      "output_format": "mp4",
      "quality_preset": "high",
      "created_at": "2026-03-24T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

Query parameters:
- `status`: Filter by status (pending, rendering, completed, failed, cancelled)
- `project_id`: Filter by project
- `limit`: Max results (default 20, max 100)
- `offset`: Pagination offset

### Get Render Queue Status

```http
GET /api/v1/render/queue

Response 200:
{
  "active_renders": 2,
  "max_concurrent": 2,
  "pending_jobs": 3,
  "max_queue_depth": 20,
  "completed_today": 7,
  "failed_today": 1,
  "average_render_time_seconds": 245.5,
  "disk_free_bytes": 50000000000,
  "disk_free_sufficient": true
}
```

### Retry Failed Render

```http
POST /api/v1/render/{job_id}/retry

Response 202:
{
  "job_id": "render_abc123",
  "status": "pending",
  "retry_count": 1,
  "max_retries": 2,
  "message": "Render job requeued for retry"
}
```

Only failed jobs can be retried. Returns 409 `RENDER_NOT_FAILED` if the job is in any other state.

### Delete Render Job

```http
DELETE /api/v1/render/{job_id}

Response 200:
{
  "job_id": "render_abc123",
  "status": "deleted",
  "output_file_deleted": false,
  "temp_files_cleaned": true,
  "message": "Render job record removed"
}
```

Removes the job record and temp files. The output file is NOT deleted (non-destructive per LRN-091). Only completed, failed, or cancelled jobs can be deleted. Active jobs must be cancelled first.

## Hardware Encoder Endpoints

### Get Hardware Encoder Status

```http
GET /api/v1/render/encoders

Response 200:
{
  "encoders": [
    {
      "name": "h264_nvenc",
      "type": "nvenc",
      "available": true,
      "priority": 10,
      "supported_formats": ["mp4", "mov"]
    },
    {
      "name": "libx264",
      "type": "software",
      "available": true,
      "priority": 100,
      "supported_formats": ["mp4", "mov"]
    },
    {
      "name": "libvpx-vp9",
      "type": "software",
      "available": true,
      "priority": 100,
      "supported_formats": ["webm"]
    }
  ],
  "detection_timestamp": "2026-03-24T12:00:00Z",
  "hardware_acceleration_available": true,
  "default_encoder_by_format": {
    "mp4": "h264_nvenc",
    "webm": "libvpx-vp9",
    "prores": "prores_ks",
    "mov": "h264_nvenc"
  }
}
```

### Refresh Hardware Detection

```http
POST /api/v1/render/encoders/refresh

Response 200:
{
  "encoders_detected": 5,
  "hardware_encoders": 2,
  "software_encoders": 3,
  "message": "Hardware encoder detection refreshed"
}
```

Forces re-detection of hardware encoders. Useful after GPU driver updates.

## Output Format Endpoints

### List Available Output Formats

```http
GET /api/v1/render/formats

Response 200:
{
  "formats": [
    {
      "id": "mp4",
      "name": "MP4 (H.264)",
      "extension": ".mp4",
      "container": "MPEG-4",
      "video_codecs": ["h264", "hevc"],
      "audio_codecs": ["aac", "flac"],
      "quality_presets": ["draft", "medium", "high", "lossless"],
      "supports_two_pass": true,
      "hardware_acceleration": true
    },
    {
      "id": "webm",
      "name": "WebM (VP9)",
      "extension": ".webm",
      "container": "WebM",
      "video_codecs": ["vp9"],
      "audio_codecs": ["opus"],
      "quality_presets": ["draft", "medium", "high", "lossless"],
      "supports_two_pass": true,
      "hardware_acceleration": false
    },
    {
      "id": "prores",
      "name": "ProRes (MOV)",
      "extension": ".mov",
      "container": "QuickTime",
      "video_codecs": ["prores"],
      "audio_codecs": ["pcm_s16le"],
      "quality_presets": ["draft", "medium", "high", "lossless"],
      "supports_two_pass": false,
      "hardware_acceleration": false
    },
    {
      "id": "mov",
      "name": "MOV (H.264)",
      "extension": ".mov",
      "container": "QuickTime",
      "video_codecs": ["h264", "hevc"],
      "audio_codecs": ["aac", "flac"],
      "quality_presets": ["draft", "medium", "high", "lossless"],
      "supports_two_pass": true,
      "hardware_acceleration": true
    }
  ]
}
```

This endpoint enables AI agents and the GUI to discover available formats and their capabilities.

## WebSocket Events (Phase 5 Additions)

All events broadcast on existing `/ws` WebSocket endpoint.

### Render Events

```json
{
  "type": "render.queued",
  "job_id": "render_abc123",
  "project_id": "proj_001",
  "output_format": "mp4",
  "quality_preset": "high",
  "queue_position": 3,
  "timestamp": "2026-03-24T12:00:00Z"
}

{
  "type": "render.started",
  "job_id": "render_abc123",
  "project_id": "proj_001",
  "encoder": "h264_nvenc",
  "hardware_accelerated": true,
  "total_frames": 9000,
  "estimated_duration_seconds": 62,
  "timestamp": "2026-03-24T12:00:02Z"
}

{
  "type": "render.progress",
  "job_id": "render_abc123",
  "progress": 0.45,
  "current_frame": 4050,
  "total_frames": 9000,
  "fps": 145.2,
  "eta_seconds": 34,
  "elapsed_seconds": 28,
  "timestamp": "2026-03-24T12:00:30Z"
}

{
  "type": "render.completed",
  "job_id": "render_abc123",
  "project_id": "proj_001",
  "output_path": "/home/user/output/my_video.mp4",
  "file_size_bytes": 375000000,
  "duration_seconds": 300.0,
  "elapsed_seconds": 62.3,
  "render_speed": "4.8x realtime",
  "timestamp": "2026-03-24T12:01:02Z"
}

{
  "type": "render.failed",
  "job_id": "render_abc123",
  "project_id": "proj_001",
  "error_code": "FFMPEG_ERROR",
  "error_message": "FFmpeg exited with code 1: Encoder not found",
  "retry_available": true,
  "retry_count": 0,
  "max_retries": 2,
  "timestamp": "2026-03-24T12:01:05Z"
}

{
  "type": "render.cancelled",
  "job_id": "render_abc123",
  "progress_at_cancel": 0.45,
  "timestamp": "2026-03-24T12:01:10Z"
}
```

### Render Frame Streaming Event

```json
{
  "type": "render.frame_available",
  "job_id": "render_abc123",
  "frame_number": 4050,
  "timestamp": "2026-03-24T12:00:30Z",
  "frame_data_url": "/api/v1/render/render_abc123/frame/latest"
}
```

Emitted periodically during rendering (throttled to max 2/sec). The `frame_data_url` returns the most recently rendered frame as JPEG at reduced resolution (540p), reusing the proxy quality infrastructure from Phase 4. This enables Theater Mode to display rendered frames as they are produced.

### Render Queue Events

```json
{
  "type": "render.queue_status",
  "active_renders": 2,
  "pending_jobs": 3,
  "timestamp": "2026-03-24T12:00:00Z"
}
```

Broadcast when queue state changes (job starts, completes, or is cancelled).

## Error Cases

All endpoints return structured errors per existing pattern:

```json
{
  "error": {
    "code": "RENDER_JOB_NOT_FOUND",
    "category": "not_found",
    "message": "Render job render_xyz789 does not exist",
    "suggestion": "List active jobs with GET /render",
    "correlation_id": "req_abc123"
  }
}
```

| Error Code | HTTP Status | Condition |
|-----------|------------|-----------|
| `RENDER_JOB_NOT_FOUND` | 404 | Job ID doesn't exist |
| `EMPTY_TIMELINE` | 422 | Cannot render a project with no clips |
| `INVALID_RENDER_SETTINGS` | 422 | Settings validation failed (details in message) |
| `OUTPUT_DIR_NOT_WRITABLE` | 422 | Cannot write to specified output directory |
| `OUTPUT_FILE_EXISTS` | 409 | Output path already exists (supply `overwrite: true` to override) |
| `INSUFFICIENT_DISK_SPACE` | 507 | Estimated output exceeds available disk space |
| `RENDER_QUEUE_FULL` | 429 | Queue at max depth, try again later |
| `RENDER_NOT_FAILED` | 409 | Retry requested on non-failed job |
| `RENDER_NOT_CANCELLABLE` | 409 | Cancel requested on completed/failed/cancelled job |
| `FFMPEG_UNAVAILABLE` | 503 | FFmpeg binary not found or not responsive |
| `ENCODER_NOT_AVAILABLE` | 422 | Requested encoder not detected on this system |
| `PROJECT_NOT_FOUND` | 404 | Referenced project doesn't exist |

## New Router Files

```
src/stoat_ferret/api/routers/
├── render.py              # EXTEND - add full render job CRUD, queue status
├── render_encoders.py     # NEW - hardware encoder status, refresh
├── render_formats.py      # NEW - output format discovery
├── preview.py             # existing (Phase 4, no changes)
├── proxy.py               # existing (Phase 4, no changes)
├── timeline.py            # existing (no changes)
├── compose.py             # existing (no changes)
├── batch.py               # existing (no changes)
├── videos.py              # existing (no changes)
├── health.py              # EXTEND - render subsystem health check
└── ...
```

**Note on existing render endpoint:** The existing `/render` endpoint from Phase 1 is a basic FFmpeg invocation. Phase 5 replaces it with the full render job system. The old endpoint will be deprecated and removed, with the new endpoint providing a superset of functionality.

## Integration with Existing Batch Render

The Phase 3 batch render endpoint (`POST /render/batch`) submits multiple render jobs. Phase 5 evolves this:
- Each item in a batch becomes a `RenderJob` in the render queue
- Batch progress aggregates per-job progress via `aggregate_segment_progress()`
- The batch endpoint remains for backward compatibility, internally creating individual render jobs
