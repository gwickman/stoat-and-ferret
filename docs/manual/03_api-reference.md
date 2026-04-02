# API Reference

Complete endpoint reference for the Stoat & Ferret REST API. All endpoints use `http://localhost:8765` as the base URL. See [API Overview](02_api-overview.md) for conventions, error format, and pagination.

---

## Health

### GET /health/live

Liveness probe. Returns 200 if the server process is running. No dependency checks.

**Response:**

```json
{"status": "ok"}
```

**Example:**

```bash
curl http://localhost:8765/health/live
```

---

### GET /health/ready

Readiness probe. Checks database connectivity and FFmpeg availability.

**Response (200 -- all healthy):**

```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "latency_ms": 0.15},
    "ffmpeg": {"status": "ok", "version": "6.0"}
  }
}
```

**Response (503 -- degraded):**

```json
{
  "status": "degraded",
  "checks": {
    "database": {"status": "ok", "latency_ms": 0.15},
    "ffmpeg": {"status": "error", "error": "ffmpeg not found in PATH"}
  }
}
```

**Example:**

```bash
curl http://localhost:8765/health/ready
```

---

## Videos

### GET /api/v1/videos

List all videos in the library with pagination.

**Query Parameters:**

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `limit` | integer | 20 | 1-100 | Max videos per page |
| `offset` | integer | 0 | 0+ | Number of videos to skip |

**Response:**

```json
{
  "videos": [
    {
      "id": "vid-abc123",
      "path": "/media/videos/clip.mp4",
      "filename": "clip.mp4",
      "duration_frames": 9000,
      "frame_rate_numerator": 30,
      "frame_rate_denominator": 1,
      "width": 1920,
      "height": 1080,
      "video_codec": "h264",
      "audio_codec": "aac",
      "file_size": 52428800,
      "thumbnail_path": "data/thumbnails/vid-abc123.jpg",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

**Example:**

```bash
curl "http://localhost:8765/api/v1/videos?limit=10&offset=0"
```

---

### GET /api/v1/videos/search

Search videos by filename or path.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | -- | Search query (min 1 character) |
| `limit` | integer | No | 20 | Max results (1-100) |

**Response:**

```json
{
  "videos": [
    {
      "id": "vid-abc123",
      "path": "/media/videos/interview.mp4",
      "filename": "interview.mp4",
      "duration_frames": 18000,
      "frame_rate_numerator": 30,
      "frame_rate_denominator": 1,
      "width": 1920,
      "height": 1080,
      "video_codec": "h264",
      "audio_codec": "aac",
      "file_size": 104857600,
      "thumbnail_path": "data/thumbnails/vid-abc123.jpg",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "query": "interview"
}
```

**Example:**

```bash
curl "http://localhost:8765/api/v1/videos/search?q=interview&limit=5"
```

---

### GET /api/v1/videos/{video_id}

Get a single video by its ID.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `video_id` | string | Unique video identifier |

**Response (200):**

```json
{
  "id": "vid-abc123",
  "path": "/media/videos/clip.mp4",
  "filename": "clip.mp4",
  "duration_frames": 9000,
  "frame_rate_numerator": 30,
  "frame_rate_denominator": 1,
  "width": 1920,
  "height": 1080,
  "video_codec": "h264",
  "audio_codec": "aac",
  "file_size": 52428800,
  "thumbnail_path": "data/thumbnails/vid-abc123.jpg",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Errors:**

- 404 `NOT_FOUND` -- Video does not exist

**Example:**

```bash
curl http://localhost:8765/api/v1/videos/vid-abc123
```

---

### GET /api/v1/videos/{video_id}/thumbnail

Get the thumbnail image for a video. Returns a JPEG image. If no thumbnail has been generated, returns a placeholder image.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `video_id` | string | Unique video identifier |

**Response:** `image/jpeg` binary data

**Errors:**

- 404 `NOT_FOUND` -- Video does not exist

**Example:**

```bash
curl -o thumbnail.jpg http://localhost:8765/api/v1/videos/vid-abc123/thumbnail
```

---

### POST /api/v1/videos/scan

Submit an asynchronous directory scan job. The server discovers video files using FFmpeg probing, extracts metadata, and generates thumbnails.

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | Yes | -- | Absolute path to directory |
| `recursive` | boolean | No | `true` | Recurse into subdirectories |

**Response (202 Accepted):**

```json
{"job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
```

**Errors:**

- 400 `INVALID_PATH` -- Path is not a valid directory
- 403 `PATH_NOT_ALLOWED` -- Path is outside configured allowed scan roots

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/videos/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/media/videos", "recursive": true}'
```

After submission, poll the job status endpoint to track progress. See [GET /api/v1/jobs/{job_id}](#get-apiv1jobsjob_id).

---

### DELETE /api/v1/videos/{video_id}

Remove a video from the library. Optionally delete the source file from disk.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `video_id` | string | Unique video identifier |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delete_file` | boolean | `false` | Also delete the source file from disk |

**Response:** 204 No Content (empty body)

**Errors:**

- 404 `NOT_FOUND` -- Video does not exist

**Examples:**

```bash
# Remove from library only
curl -X DELETE http://localhost:8765/api/v1/videos/vid-abc123

# Remove from library and delete file
curl -X DELETE "http://localhost:8765/api/v1/videos/vid-abc123?delete_file=true"
```

---

## Projects

### GET /api/v1/projects

List all projects with pagination.

**Query Parameters:**

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `limit` | integer | 20 | 1-100 | Max projects per page |
| `offset` | integer | 0 | 0+ | Number to skip |

**Response:**

```json
{
  "projects": [
    {
      "id": "proj-xyz789",
      "name": "My Edit",
      "output_width": 1920,
      "output_height": 1080,
      "output_fps": 30,
      "created_at": "2025-01-15T11:00:00Z",
      "updated_at": "2025-01-15T11:00:00Z"
    }
  ],
  "total": 1
}
```

**Example:**

```bash
curl http://localhost:8765/api/v1/projects
```

---

### POST /api/v1/projects

Create a new editing project.

**Request Body:**

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `name` | string | Yes | -- | min 1 char | Project name |
| `output_width` | integer | No | 1920 | >= 1 | Output video width in pixels |
| `output_height` | integer | No | 1080 | >= 1 | Output video height in pixels |
| `output_fps` | integer | No | 30 | 1-120 | Output frame rate |

**Response (201 Created):**

```json
{
  "id": "proj-xyz789",
  "name": "My Edit",
  "output_width": 1920,
  "output_height": 1080,
  "output_fps": 30,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Edit", "output_width": 1920, "output_height": 1080, "output_fps": 30}'
```

---

### GET /api/v1/projects/{project_id}

Get a project by ID.

**Response (200):**

```json
{
  "id": "proj-xyz789",
  "name": "My Edit",
  "output_width": 1920,
  "output_height": 1080,
  "output_fps": 30,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

**Errors:**

- 404 `NOT_FOUND` -- Project does not exist

**Example:**

```bash
curl http://localhost:8765/api/v1/projects/proj-xyz789
```

---

### DELETE /api/v1/projects/{project_id}

Delete a project.

**Response:** 204 No Content (empty body)

**Errors:**

- 404 `NOT_FOUND` -- Project does not exist

**Example:**

```bash
curl -X DELETE http://localhost:8765/api/v1/projects/proj-xyz789
```

---

### GET /api/v1/projects/{project_id}/clips

List all clips in a project, ordered by timeline position.

**Response:**

```json
{
  "clips": [
    {
      "id": "clip-def456",
      "project_id": "proj-xyz789",
      "source_video_id": "vid-abc123",
      "in_point": 0,
      "out_point": 900,
      "timeline_position": 0,
      "effects": [
        {
          "effect_type": "text_overlay",
          "parameters": {"text": "Title", "fontsize": 48},
          "filter_string": "drawtext=text='Title':fontsize=48"
        }
      ],
      "created_at": "2025-01-15T11:05:00Z",
      "updated_at": "2025-01-15T11:10:00Z"
    }
  ],
  "total": 1
}
```

**Errors:**

- 404 `NOT_FOUND` -- Project does not exist

**Example:**

```bash
curl http://localhost:8765/api/v1/projects/proj-xyz789/clips
```

---

### POST /api/v1/projects/{project_id}/clips

Add a clip to a project's timeline. All time values are in **frames** (integers), not seconds.

**Request Body:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `source_video_id` | string | Yes | Must exist in library | ID of the source video |
| `in_point` | integer | Yes | >= 0 | Start frame in source video |
| `out_point` | integer | Yes | >= 0 | End frame in source video |
| `timeline_position` | integer | Yes | >= 0 | Position on the timeline (in frames) |

**Response (201 Created):**

```json
{
  "id": "clip-def456",
  "project_id": "proj-xyz789",
  "source_video_id": "vid-abc123",
  "in_point": 0,
  "out_point": 900,
  "timeline_position": 0,
  "effects": null,
  "created_at": "2025-01-15T11:05:00Z",
  "updated_at": "2025-01-15T11:05:00Z"
}
```

**Errors:**

- 404 `NOT_FOUND` -- Project or source video does not exist
- 400 `VALIDATION_ERROR` -- Clip fails Rust core validation (e.g., `out_point > duration_frames`)

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/projects/proj-xyz789/clips \
  -H "Content-Type: application/json" \
  -d '{
    "source_video_id": "vid-abc123",
    "in_point": 0,
    "out_point": 900,
    "timeline_position": 0
  }'
```

---

### PATCH /api/v1/projects/{project_id}/clips/{clip_id}

Update clip properties. Only provided fields are modified.

**Request Body (all fields optional):**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `in_point` | integer | >= 0 | New start frame |
| `out_point` | integer | >= 0 | New end frame |
| `timeline_position` | integer | >= 0 | New timeline position |

**Response (200):**

Returns the updated `ClipResponse` object.

**Errors:**

- 404 `NOT_FOUND` -- Project, clip, or source video does not exist
- 400 `VALIDATION_ERROR` -- Updated values fail Rust core validation

**Example:**

```bash
curl -X PATCH http://localhost:8765/api/v1/projects/proj-xyz789/clips/clip-def456 \
  -H "Content-Type: application/json" \
  -d '{"in_point": 150, "out_point": 1050}'
```

---

### DELETE /api/v1/projects/{project_id}/clips/{clip_id}

Remove a clip from a project.

**Response:** 204 No Content (empty body)

**Errors:**

- 404 `NOT_FOUND` -- Clip does not exist or does not belong to this project

**Example:**

```bash
curl -X DELETE http://localhost:8765/api/v1/projects/proj-xyz789/clips/clip-def456
```

---

## Jobs

### GET /api/v1/jobs/{job_id}

Get the status of an asynchronous job (e.g., a video scan).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Job identifier returned by scan endpoint |

**Response:**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "complete",
  "progress": 1.0,
  "result": {
    "scanned": 15,
    "new": 12,
    "updated": 3,
    "skipped": 0,
    "errors": []
  },
  "error": null
}
```

**Job Statuses:**

| Status | Description |
|--------|-------------|
| `pending` | Job is queued but not yet started |
| `running` | Job is currently executing |
| `complete` | Job finished successfully (`result` field populated) |
| `failed` | Job encountered an error (`error` field populated) |
| `timeout` | Job exceeded its time limit |
| `cancelled` | Job was cancelled by the user |

**Errors:**

- 404 `NOT_FOUND` -- Job ID does not exist

**Example:**

```bash
curl http://localhost:8765/api/v1/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

## Effects

### GET /api/v1/effects

List all available effects with their metadata, JSON parameter schemas, AI hints, and filter preview strings.

**Response:**

```json
{
  "effects": [
    {
      "effect_type": "text_overlay",
      "name": "Text Overlay",
      "description": "Add text overlays to video with customizable font, position, and styling.",
      "parameter_schema": {
        "type": "object",
        "properties": {
          "text": {"type": "string", "description": "The text to display"},
          "fontsize": {"type": "integer", "default": 48, "description": "Font size in pixels"},
          "fontcolor": {"type": "string", "default": "white", "description": "Font color name or hex value"},
          "position": {
            "type": "string",
            "enum": ["center", "bottom_center", "top_left", "top_right", "bottom_left", "bottom_right"],
            "default": "bottom_center"
          },
          "margin": {"type": "integer", "default": 10},
          "font": {"type": "string"}
        },
        "required": ["text"]
      },
      "ai_hints": {
        "text": "The text content to overlay on the video",
        "fontsize": "Font size in pixels, typical range 12-72"
      },
      "filter_preview": "drawtext=text='Sample Text':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-text_h-20"
    }
  ],
  "total": 9
}
```

**Example:**

```bash
curl http://localhost:8765/api/v1/effects
```

---

### POST /api/v1/effects/preview

Preview the FFmpeg filter string that would be generated for an effect, without applying it to any clip.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `effect_type` | string | Yes | Effect type key |
| `parameters` | object | Yes | Effect parameters |

**Response:**

```json
{
  "effect_type": "text_overlay",
  "filter_string": "drawtext=text='Hello':fontsize=36:fontcolor=yellow:x=(w-text_w)/2:y=h-text_h-10"
}
```

**Errors:**

- 400 `EFFECT_NOT_FOUND` -- Unknown effect type
- 400 `INVALID_EFFECT_PARAMS` -- Parameters fail schema validation

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/effects/preview \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "text_overlay",
    "parameters": {"text": "Hello", "fontsize": 36, "fontcolor": "yellow"}
  }'
```

---

### POST /api/v1/projects/{project_id}/clips/{clip_id}/effects

Apply an effect to a clip. The effect is appended to the clip's effect stack.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `effect_type` | string | Yes | Effect type key (e.g., `text_overlay`, `speed_control`) |
| `parameters` | object | Yes | Effect parameters matching the schema |

**Response (201 Created):**

```json
{
  "effect_type": "video_fade",
  "parameters": {"fade_type": "in", "duration": 1.5},
  "filter_string": "fade=t=in:d=1.5"
}
```

**Errors:**

- 404 `NOT_FOUND` -- Project or clip does not exist
- 400 `EFFECT_NOT_FOUND` -- Unknown effect type
- 400 `INVALID_EFFECT_PARAMS` -- Parameters fail schema validation

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/projects/proj-xyz789/clips/clip-def456/effects \
  -H "Content-Type: application/json" \
  -d '{"effect_type": "video_fade", "parameters": {"fade_type": "in", "duration": 1.5}}'
```

---

### PATCH /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index}

Update an effect at a specific index in the clip's effect stack. The effect type is preserved; only parameters can change.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `index` | integer | Zero-based index in the effects list |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parameters` | object | Yes | New parameters for the effect |

**Response (200):**

```json
{
  "effect_type": "video_fade",
  "parameters": {"fade_type": "in", "duration": 2.0},
  "filter_string": "fade=t=in:d=2.0"
}
```

**Errors:**

- 404 `NOT_FOUND` -- Project, clip, or effect index not found
- 400 `INVALID_EFFECT_PARAMS` -- New parameters fail schema validation

**Example:**

```bash
curl -X PATCH http://localhost:8765/api/v1/projects/proj-xyz789/clips/clip-def456/effects/0 \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"fade_type": "in", "duration": 2.0}}'
```

---

### DELETE /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index}

Remove an effect at a specific index from the clip's effect stack. Remaining effects shift down.

**Response (200):**

```json
{
  "index": 0,
  "deleted_effect_type": "video_fade"
}
```

**Errors:**

- 404 `NOT_FOUND` -- Project, clip, or effect index not found

**Example:**

```bash
curl -X DELETE http://localhost:8765/api/v1/projects/proj-xyz789/clips/clip-def456/effects/0
```

---

### POST /api/v1/projects/{project_id}/effects/transition

Apply a transition between two adjacent clips in the project timeline. The source clip must immediately precede the target clip in timeline order.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_clip_id` | string | Yes | ID of the first (outgoing) clip |
| `target_clip_id` | string | Yes | ID of the second (incoming) clip |
| `transition_type` | string | Yes | Transition effect key (e.g., `xfade`, `acrossfade`) |
| `parameters` | object | Yes | Transition parameters |

**Response (201 Created):**

```json
{
  "source_clip_id": "clip-001",
  "target_clip_id": "clip-002",
  "transition_type": "xfade",
  "parameters": {"transition": "fade", "duration": 1.0, "offset": 4.0},
  "filter_string": "xfade=transition=fade:duration=1.0:offset=4.0"
}
```

**Errors:**

- 404 `NOT_FOUND` -- Project or clip does not exist
- 400 `SAME_CLIP` -- Source and target are the same clip
- 400 `EMPTY_TIMELINE` -- Project has no clips
- 400 `NOT_ADJACENT` -- Clips are not adjacent in the timeline
- 400 `EFFECT_NOT_FOUND` -- Unknown transition type
- 400 `INVALID_EFFECT_PARAMS` -- Parameters fail schema validation

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/projects/proj-xyz789/effects/transition \
  -H "Content-Type: application/json" \
  -d '{
    "source_clip_id": "clip-001",
    "target_clip_id": "clip-002",
    "transition_type": "xfade",
    "parameters": {"transition": "fade", "duration": 1.0, "offset": 4.0}
  }'
```

---

## Render

### POST /api/v1/render

Submit a render job for a project. The server queues the job and begins rendering asynchronously.

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_id` | string | Yes | -- | Project UUID to render |
| `output_format` | string | No | `"mp4"` | Output container format (`mp4`, `webm`, `mov`, `mkv`) |
| `quality_preset` | string | No | `"standard"` | Quality preset (`draft`, `standard`, `high`) |
| `render_plan` | string | No | `"{}"` | Serialized render plan JSON |

**Response (201 Created):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "project_id": "proj-xyz789",
  "status": "queued",
  "output_path": "/output/proj-xyz789_20250115T110000.mp4",
  "output_format": "mp4",
  "quality_preset": "standard",
  "progress": 0.0,
  "error_message": null,
  "retry_count": 0,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z",
  "completed_at": null
}
```

**Errors:**

- 400 `INVALID_FORMAT` -- Unknown output format
- 400 `INVALID_PRESET` -- Unknown quality preset
- 422 `PREFLIGHT_FAILED` -- Pre-flight validation failed (settings, disk space, or queue capacity)
- 503 `RENDER_UNAVAILABLE` -- Render service unavailable (shutting down or FFmpeg not installed)

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/render \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-xyz789", "output_format": "mp4", "quality_preset": "high"}'
```

---

### GET /api/v1/render/{job_id}

Get the status of a render job by its ID.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Render job UUID |

**Response (200):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "project_id": "proj-xyz789",
  "status": "running",
  "output_path": "/output/proj-xyz789_20250115T110000.mp4",
  "output_format": "mp4",
  "quality_preset": "standard",
  "progress": 0.45,
  "error_message": null,
  "retry_count": 0,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:30Z",
  "completed_at": null
}
```

**Render Job Statuses:**

| Status | Description |
|--------|-------------|
| `queued` | Job is queued, waiting to start |
| `running` | Job is currently rendering |
| `completed` | Render finished successfully |
| `failed` | Render encountered an error |
| `cancelled` | Job was cancelled by the user |

**Errors:**

- 404 `NOT_FOUND` -- Render job does not exist

**Example:**

```bash
curl http://localhost:8765/api/v1/render/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

### GET /api/v1/render

List all render jobs with pagination and optional status filter.

**Query Parameters:**

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `limit` | integer | 20 | 1-100 | Max jobs per page |
| `offset` | integer | 0 | 0+ | Number of jobs to skip |
| `status` | string | -- | -- | Filter by status (`queued`, `running`, `completed`, `failed`, `cancelled`) |

**Response:**

```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "project_id": "proj-xyz789",
      "status": "completed",
      "output_path": "/output/proj-xyz789_20250115T110000.mp4",
      "output_format": "mp4",
      "quality_preset": "standard",
      "progress": 1.0,
      "error_message": null,
      "retry_count": 0,
      "created_at": "2025-01-15T11:00:00Z",
      "updated_at": "2025-01-15T11:05:00Z",
      "completed_at": "2025-01-15T11:05:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

**Errors:**

- 400 `INVALID_STATUS` -- Invalid status filter value

**Example:**

```bash
curl "http://localhost:8765/api/v1/render?status=completed&limit=10"
```

---

### POST /api/v1/render/{job_id}/cancel

Cancel a queued or running render job. Terminates the active FFmpeg process if running.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Render job UUID |

**Response (200):**

Returns the updated `RenderJobResponse` with status set to `cancelled`.

**Errors:**

- 404 `NOT_FOUND` -- Render job does not exist
- 409 `NOT_CANCELLABLE` -- Job is not in a cancellable state (must be `queued` or `running`)
- 409 `CANCEL_FAILED` -- Failed to terminate the FFmpeg process

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/render/a1b2c3d4-e5f6-7890-abcd-ef1234567890/cancel
```

---

### POST /api/v1/render/{job_id}/retry

Retry a failed render job. Requeues the job with progress reset to 0.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Render job UUID |

**Response (200):**

Returns the updated `RenderJobResponse` with status reset to `queued`, progress reset to `0.0`, and `retry_count` incremented.

**Errors:**

- 404 `NOT_FOUND` -- Render job does not exist
- 409 `NOT_RETRYABLE` -- Job is not in `failed` status
- 409 `PERMANENT_FAILURE` -- Retry count exceeds maximum allowed retries

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/render/a1b2c3d4-e5f6-7890-abcd-ef1234567890/retry
```

---

### DELETE /api/v1/render/{job_id}

Delete a render job record. Output files are preserved on disk.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Render job UUID |

**Response (200):**

Returns the deleted job's final `RenderJobResponse` state.

**Errors:**

- 404 `NOT_FOUND` -- Render job does not exist

**Example:**

```bash
curl -X DELETE http://localhost:8765/api/v1/render/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

### GET /api/v1/render/encoders

List available FFmpeg encoders. Returns cached results if available; triggers lazy detection in background if cache is empty.

**Response:**

```json
{
  "encoders": [
    {
      "name": "h264_nvenc",
      "codec": "h264",
      "is_hardware": true,
      "encoder_type": "Nvenc",
      "description": "NVIDIA NVENC H.264 encoder",
      "detected_at": "2025-01-15T10:00:00Z"
    },
    {
      "name": "libx264",
      "codec": "h264",
      "is_hardware": false,
      "encoder_type": "Software",
      "description": "libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
      "detected_at": "2025-01-15T10:00:00Z"
    }
  ],
  "cached": true
}
```

**Errors:**

- 503 `FFMPEG_UNAVAILABLE` -- FFmpeg binary not found in PATH
- 503 `DETECTION_FAILED` -- Encoder detection subprocess error

**Example:**

```bash
curl http://localhost:8765/api/v1/render/encoders
```

---

### POST /api/v1/render/encoders/refresh

Force re-detection of available FFmpeg encoders. Clears the cache and runs a fresh detection.

**Response:**

Returns `EncoderListResponse` with freshly detected encoders and `cached` set to `false`.

**Errors:**

- 409 `REFRESH_IN_PROGRESS` -- Another encoder refresh is currently running
- 503 `FFMPEG_UNAVAILABLE` -- FFmpeg binary not found in PATH
- 503 `DETECTION_FAILED` -- Encoder detection subprocess error

**Example:**

```bash
curl -X POST http://localhost:8765/api/v1/render/encoders/refresh
```

---

### GET /api/v1/render/formats

List supported output formats with codec details and capability flags.

**Response:**

```json
{
  "formats": [
    {
      "format": "mp4",
      "extension": ".mp4",
      "mime_type": "video/mp4",
      "codecs": [
        {
          "name": "h264",
          "quality_presets": [
            {"preset": "draft", "video_bitrate_kbps": 1500},
            {"preset": "standard", "video_bitrate_kbps": 5000},
            {"preset": "high", "video_bitrate_kbps": 15000}
          ]
        },
        {
          "name": "h265",
          "quality_presets": [
            {"preset": "draft", "video_bitrate_kbps": 1000},
            {"preset": "standard", "video_bitrate_kbps": 3500},
            {"preset": "high", "video_bitrate_kbps": 10000}
          ]
        }
      ],
      "supports_hw_accel": true,
      "supports_two_pass": true,
      "supports_alpha": false
    }
  ]
}
```

**Format Summary:**

| Format | Codecs | HW Accel | Two-Pass | Alpha |
|--------|--------|----------|----------|-------|
| `mp4` | h264, h265 | Yes | Yes | No |
| `webm` | vp8, vp9 | No | Yes | Yes |
| `mov` | h264, prores | Yes | Yes | Yes |
| `mkv` | h264, h265, vp9 | Yes | Yes | Yes |

**Example:**

```bash
curl http://localhost:8765/api/v1/render/formats
```

---

### GET /api/v1/render/queue

Get the current render queue status including job counts and disk space.

**Response:**

```json
{
  "active_count": 1,
  "pending_count": 3,
  "max_concurrent": 2,
  "max_queue_depth": 10,
  "disk_available_bytes": 107374182400,
  "disk_total_bytes": 536870912000,
  "completed_today": 5,
  "failed_today": 0
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `active_count` | integer | Currently running render jobs |
| `pending_count` | integer | Queued jobs waiting to start |
| `max_concurrent` | integer | Maximum simultaneous running jobs |
| `max_queue_depth` | integer | Maximum queued jobs before rejection |
| `disk_available_bytes` | integer | Available disk space in render output directory |
| `disk_total_bytes` | integer | Total disk space on render output volume |
| `completed_today` | integer | Jobs completed since midnight UTC |
| `failed_today` | integer | Jobs failed since midnight UTC |

**Example:**

```bash
curl http://localhost:8765/api/v1/render/queue
```

---

## WebSocket

### WS /ws

Connect to the WebSocket endpoint for real-time event notifications.

**Connection:**

```
ws://localhost:8765/ws
```

**Events sent by server:**

| Event Type | Description |
|------------|-------------|
| `heartbeat` | Periodic keepalive (default 30s interval) |
| `health_status` | Health status change |
| `scan_started` | Scan job has started |
| `scan_completed` | Scan job has finished |
| `project_created` | New project was created |

**Event Format:**

```json
{
  "type": "heartbeat",
  "payload": {},
  "correlation_id": null,
  "timestamp": "2025-01-15T10:30:00.000000+00:00"
}
```

**Example (Python):**

```python
import asyncio
import websockets

async def listen():
    async with websockets.connect("ws://localhost:8765/ws") as ws:
        while True:
            message = await ws.recv()
            print(message)

asyncio.run(listen())
```

---

## Metrics

### GET /metrics

Prometheus-compatible metrics endpoint. Exposes request counts, latencies, effect application counts, and other operational metrics.

**Example:**

```bash
curl http://localhost:8765/metrics
```

---

## OpenAPI

### GET /openapi.json

Machine-readable OpenAPI 3.x schema for the entire API.

### GET /docs

Swagger UI -- interactive API explorer.

### GET /redoc

ReDoc -- clean, readable API documentation.

---

## Response Schemas Reference

### VideoResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique video identifier |
| `path` | string | Absolute file path |
| `filename` | string | File name only |
| `duration_frames` | integer | Total duration in frames |
| `frame_rate_numerator` | integer | Frame rate numerator |
| `frame_rate_denominator` | integer | Frame rate denominator |
| `width` | integer | Video width in pixels |
| `height` | integer | Video height in pixels |
| `video_codec` | string | Video codec name |
| `audio_codec` | string or null | Audio codec name |
| `file_size` | integer | File size in bytes |
| `thumbnail_path` | string or null | Path to generated thumbnail |
| `created_at` | datetime | When the video was added |
| `updated_at` | datetime | Last update time |

### ProjectResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique project identifier |
| `name` | string | Project name |
| `output_width` | integer | Output width in pixels |
| `output_height` | integer | Output height in pixels |
| `output_fps` | integer | Output frame rate |
| `created_at` | datetime | Creation time |
| `updated_at` | datetime | Last update time |

### ClipResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique clip identifier |
| `project_id` | string | Parent project ID |
| `source_video_id` | string | Source video ID |
| `in_point` | integer | Start frame in source video |
| `out_point` | integer | End frame in source video |
| `timeline_position` | integer | Position on the timeline (in frames) |
| `effects` | array or null | List of applied effects |
| `created_at` | datetime | Creation time |
| `updated_at` | datetime | Last update time |

### JobStatusResponse

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `status` | string | `pending`, `running`, `complete`, `failed`, `timeout`, or `cancelled` |
| `progress` | float or null | Normalized progress (0.0-1.0) |
| `result` | any or null | Job result when complete |
| `error` | string or null | Error message when failed |

### RenderJobResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique render job identifier (UUID) |
| `project_id` | string | Project being rendered |
| `status` | string | `queued`, `running`, `completed`, `failed`, or `cancelled` |
| `output_path` | string | Full file path for rendered output |
| `output_format` | string | Container format (`mp4`, `webm`, `mov`, `mkv`) |
| `quality_preset` | string | Quality preset (`draft`, `standard`, `high`) |
| `progress` | float | Render progress (0.0-1.0) |
| `error_message` | string or null | Error description if failed |
| `retry_count` | integer | Number of retry attempts |
| `created_at` | datetime | Job creation time |
| `updated_at` | datetime | Last update time |
| `completed_at` | datetime or null | Completion time (null if not terminal) |

### QueueStatusResponse

| Field | Type | Description |
|-------|------|-------------|
| `active_count` | integer | Currently running render jobs |
| `pending_count` | integer | Queued jobs waiting to start |
| `max_concurrent` | integer | Maximum simultaneous running jobs |
| `max_queue_depth` | integer | Maximum queued jobs before rejection |
| `disk_available_bytes` | integer | Available disk space in render output directory |
| `disk_total_bytes` | integer | Total disk space on render output volume |
| `completed_today` | integer | Jobs completed since midnight UTC |
| `failed_today` | integer | Jobs failed since midnight UTC |

### EncoderInfoResponse

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Encoder name as reported by FFmpeg |
| `codec` | string | Codec identifier (e.g., `h264`, `hevc`) |
| `is_hardware` | boolean | Whether hardware-accelerated |
| `encoder_type` | string | Type classification (e.g., `Software`, `Nvenc`, `Qsv`) |
| `description` | string | Encoder description from FFmpeg |
| `detected_at` | datetime | When the encoder was detected |

### FormatInfo

| Field | Type | Description |
|-------|------|-------------|
| `format` | string | Format identifier (`mp4`, `webm`, `mov`, `mkv`) |
| `extension` | string | File extension with dot (e.g., `.mp4`) |
| `mime_type` | string | MIME type (e.g., `video/mp4`) |
| `codecs` | array | Supported codecs with quality presets |
| `supports_hw_accel` | boolean | Hardware-accelerated encoding available |
| `supports_two_pass` | boolean | Two-pass encoding supported |
| `supports_alpha` | boolean | Alpha channel transparency supported |
