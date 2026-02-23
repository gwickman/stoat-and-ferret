# stoat-and-ferret - API Specification

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

This API specification describes the FastAPI-based REST interface for the AI-driven video editor. The HTTP layer is implemented in Python for **AI discoverability** and **rapid iteration**, while compute-intensive operations (timeline calculations, filter generation, input sanitization) are handled by the **Rust core** for performance and safety.

**Architecture Note:**
- Python/FastAPI handles HTTP requests, validation, and orchestration
- Rust core generates filter strings, validates inputs, and calculates timelines
- Filter strings in responses show exactly what FFmpeg will receive (transparency)

---

## Design Principles

### AI-First Design
- **Self-documenting**: Endpoint names clearly describe their purpose
- **Discoverable**: `GET /effects` returns all available effects with schemas
- **Predictable**: Consistent patterns across all endpoints
- **Helpful errors**: Error messages include suggestions for fixing issues
- **Transparent**: Responses include generated filter strings for debugging

### REST Conventions
- **Resources**: Plural nouns (`/videos`, `/projects`, `/clips`)
- **Actions**: HTTP verbs (GET, POST, PATCH, DELETE)
- **Relationships**: Nested routes (`/projects/{id}/clips`)
- **Filtering**: Query parameters (`?q=search&limit=20`)

---

## Base URL

```
http://localhost:8000/api/v1
```

---

## Authentication

For single-user deployment, authentication is optional. Multi-user scenarios can use:

```http
Authorization: Bearer <token>
```

---

## Endpoint Reference

### Endpoint Group Summary

| Group | Purpose |
|-------|---------|
| `/videos` | Library management (CRUD, scan, search) |
| `/jobs` | Async job status polling |
| `/projects` | Project/timeline management |
| `/clips` | Clip operations within projects |
| `/effects` | Effect application, transitions, and discovery |
| `/render` | Export job management |
| `/health` | Health checks (liveness, readiness) |
| `/system` | System information |
| `/ws` | WebSocket endpoint for real-time events |
| `/gui` | Static file serving for React frontend |

---

### System & Health

#### Get System Info
```http
GET /system/info
```

**Response:** `200 OK`
```json
{
  "version": "0.1.0",
  "rust_core_version": "0.1.0",
  "python_version": "3.11.5",
  "ffmpeg_version": "6.0",
  "api_version": "v1"
}
```

---

#### Health Check (Liveness)
```http
GET /health/live
```

**Response:** `200 OK`
```json
{
  "status": "ok"
}
```

---

#### Health Check (Readiness)
```http
GET /health/ready
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "latency_ms": 1.2},
    "ffmpeg": {"status": "ok", "version": "6.0"},
    "rust_core": {"status": "ok", "version": "0.1.0"},
    "redis": {"status": "ok", "connected": true}
  }
}
```

---

### Videos (Library Management)

#### List Videos
```http
GET /videos
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Results per page (max 100) |
| `offset` | int | 0 | Pagination offset |
| `sort` | string | `modified_desc` | Sort order |

**Sort Options:** `name_asc`, `name_desc`, `duration_asc`, `duration_desc`, `modified_asc`, `modified_desc`, `created_asc`, `created_desc`

**Response:** `200 OK`
```json
{
  "videos": [
    {
      "id": 1,
      "path": "/home/user/videos/clip.mp4",
      "filename": "clip.mp4",
      "duration": 125.5,
      "width": 1920,
      "height": 1080,
      "fps": 30.0,
      "codec": "h264",
      "thumbnail": "/thumbnails/1.jpg",
      "modified_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 47,
  "limit": 20,
  "offset": 0
}
```

---

#### Get Video Details
```http
GET /videos/{id}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "path": "/home/user/videos/clip.mp4",
  "filename": "clip.mp4",
  "duration": 125.5,
  "width": 1920,
  "height": 1080,
  "fps": 30.0,
  "codec": "h264",
  "profile": "High",
  "level": "4.1",
  "pixel_format": "yuv420p",
  "audio_codec": "aac",
  "audio_channels": 2,
  "audio_sample_rate": 48000,
  "bitrate": 8000000,
  "file_size": 125000000,
  "thumbnail": "/thumbnails/1.jpg",
  "created_at": "2024-06-15T14:30:00Z",
  "scanned_at": "2024-01-15T10:30:00Z",
  "metadata": {
    "creation_time": "2024-06-15T14:30:00Z",
    "encoder": "Lavf58.76.100"
  }
}
```

---

#### Search Videos
```http
GET /videos/search
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `limit` | int | No | Results per page (default 20) |
| `offset` | int | No | Pagination offset |

**Search Syntax:**
- Simple terms: `vacation beach`
- Phrase: `"summer 2024"`
- Boolean: `vacation AND 2024`
- Exclude: `vacation NOT work`

**Response:** `200 OK`
```json
{
  "videos": [...],
  "total": 5,
  "query": "vacation AND 2024"
}
```

---

#### Scan Directory (Async)
```http
POST /videos/scan
```

Submits a directory scan as an asynchronous job. Returns immediately with a job ID for polling.

**Request Body:**
```json
{
  "path": "/home/user/videos",
  "recursive": true
}
```

**Note:** Path validation is performed synchronously before job submission. The directory must exist.

**Response:** `202 Accepted`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

Use `GET /jobs/{job_id}` to poll for scan progress and results. When the job completes, the `result` field contains the scan summary:

```json
{
  "scanned": 47,
  "new": 12,
  "updated": 3,
  "skipped": 32,
  "errors": [
    {
      "path": "/home/user/videos/corrupt.mp4",
      "error": "Could not read file metadata"
    }
  ]
}
```

---

### Jobs (Async Job Status)

#### Get Job Status
```http
GET /jobs/{job_id}
```

Poll the status of an asynchronous job submitted via endpoints like `POST /videos/scan`.

**Response (Pending):** `200 OK`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "progress": null,
  "result": null,
  "error": null
}
```

**Response (Running):** `200 OK`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "progress": null,
  "result": null,
  "error": null
}
```

**Response (Complete):** `200 OK`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "complete",
  "progress": null,
  "result": {
    "scanned": 47,
    "new": 12,
    "updated": 3,
    "skipped": 32,
    "errors": []
  },
  "error": null
}
```

**Response (Failed):** `200 OK`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failed",
  "progress": null,
  "result": null,
  "error": "Scan failed: permission denied"
}
```

**Response (Timeout):** `200 OK`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "timeout",
  "progress": null,
  "result": null,
  "error": "Job timed out after 300.0s"
}
```

**Error Response:** `404 Not Found`
```json
{
  "detail": {
    "code": "NOT_FOUND",
    "message": "Job a1b2c3d4-... not found"
  }
}
```

**Job Statuses:**

| Status | Description |
|--------|-------------|
| `pending` | Job is queued, waiting to be processed |
| `running` | Job is currently being executed |
| `complete` | Job finished successfully; result available |
| `failed` | Job encountered an error; error message available |
| `timeout` | Job exceeded the configured timeout (default 300s) |
| `cancelled` | Job was cancelled by the user; partial results may be available |

---

#### Cancel Job
```http
POST /jobs/{job_id}/cancel
```

Request cooperative cancellation of a running job. The job will stop at its next checkpoint and preserve any partial results.

**Success Response:** `200 OK`
```json
{
  "job_id": "a1b2c3d4-...",
  "status": "pending",
  "progress": 0.3,
  "result": null,
  "error": null
}
```

**Error Response:** `404 Not Found`
```json
{
  "detail": {
    "code": "NOT_FOUND",
    "message": "Job a1b2c3d4-... not found"
  }
}
```

**Error Response:** `409 Conflict` (job already in terminal state)
```json
{
  "detail": {
    "code": "ALREADY_TERMINAL",
    "message": "Job a1b2c3d4-... is already complete"
  }
}
```

---

#### Delete Video from Library
```http
DELETE /videos/{id}
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delete_file` | bool | false | Also delete source file |

**Response:** `204 No Content`

---

### Projects (Timeline Management)

#### List Projects
```http
GET /projects
```

**Response:** `200 OK`
```json
{
  "projects": [
    {
      "id": "proj_abc123",
      "name": "Vacation Highlights",
      "created_at": "2024-01-15T10:30:00Z",
      "modified_at": "2024-01-15T14:22:00Z",
      "duration": 45.5,
      "clip_count": 5
    }
  ]
}
```

---

#### Create Project
```http
POST /projects
```

**Request Body:**
```json
{
  "name": "My Video Project",
  "output": {
    "width": 1920,
    "height": 1080,
    "fps": 30
  }
}
```

**Response:** `201 Created`
```json
{
  "id": "proj_abc123",
  "name": "My Video Project",
  "created_at": "2024-01-15T10:30:00Z",
  "modified_at": "2024-01-15T10:30:00Z",
  "output": {
    "width": 1920,
    "height": 1080,
    "fps": 30
  },
  "tracks": [],
  "duration": 0
}
```

---

#### Get Project
```http
GET /projects/{id}
```

**Response:** `200 OK`
```json
{
  "id": "proj_abc123",
  "name": "My Video Project",
  "created_at": "2024-01-15T10:30:00Z",
  "modified_at": "2024-01-15T14:22:00Z",
  "output": {
    "width": 1920,
    "height": 1080,
    "fps": 30
  },
  "tracks": [
    {
      "id": "track_video_main",
      "type": "video",
      "clips": [
        {
          "id": "clip_001",
          "source": "/home/user/videos/intro.mp4",
          "in_point": 0,
          "out_point": 15.0,
          "timeline_start": 0,
          "timeline_end": 15.0,
          "effects": []
        }
      ]
    }
  ],
  "duration": 15.0
}
```

---

#### Get Project Timeline (Detailed)
```http
GET /projects/{id}/timeline
```

Returns timeline with all calculated positions. Timeline calculations are performed by Rust core.

**Response:** `200 OK`
```json
{
  "project_id": "proj_abc123",
  "total_duration": 45.5,
  "calculated_at": "2024-01-15T14:22:00Z",
  "calculation_time_ms": 2.3,
  "clips": [
    {
      "id": "clip_001",
      "source": "/home/user/videos/intro.mp4",
      "in_point": 0,
      "out_point": 15.0,
      "timeline_start": 0,
      "timeline_end": 15.0,
      "source_duration": 15.0,
      "effective_duration": 15.0,
      "speed_factor": 1.0,
      "effects": [
        {
          "id": "effect_001",
          "type": "text_overlay",
          "start_absolute": 0,
          "end_absolute": 4.0
        }
      ]
    },
    {
      "id": "clip_002",
      "source": "/home/user/videos/main.mp4",
      "in_point": 10.0,
      "out_point": 25.0,
      "timeline_start": 15.0,
      "timeline_end": 30.0,
      "source_duration": 15.0,
      "effective_duration": 15.0,
      "speed_factor": 1.0,
      "effects": []
    }
  ]
}
```

---

#### Update Project
```http
PATCH /projects/{id}
```

**Request Body:**
```json
{
  "name": "Updated Project Name",
  "output": {
    "fps": 60
  }
}
```

**Response:** `200 OK`

---

#### Delete Project
```http
DELETE /projects/{id}
```

**Response:** `204 No Content`

---

### Clips (Within Projects)

#### Add Clip
```http
POST /projects/{project_id}/clips
```

**Request Body:**
```json
{
  "source": "/home/user/videos/clip.mp4",
  "in_point": 10.0,
  "out_point": 25.0,
  "position": "end"
}
```

**Position Options:**
- `end`: Append to end of timeline
- `start`: Insert at beginning
- `after:{clip_id}`: Insert after specific clip

**Note:** Path validation and time range validation performed by Rust core.

**Response:** `201 Created`
```json
{
  "id": "clip_xyz789",
  "source": "/home/user/videos/clip.mp4",
  "in_point": 10.0,
  "out_point": 25.0,
  "timeline_start": 15.0,
  "timeline_end": 30.0,
  "duration": 15.0,
  "effects": []
}
```

---

#### Update Clip
```http
PATCH /projects/{project_id}/clips/{clip_id}
```

**Request Body:**
```json
{
  "in_point": 12.0,
  "out_point": 22.0
}
```

**Response:** `200 OK`

---

#### Reorder Clips
```http
POST /projects/{project_id}/clips/reorder
```

**Request Body:**
```json
{
  "order": ["clip_001", "clip_003", "clip_002"]
}
```

**Note:** Timeline recalculation performed by Rust core.

**Response:** `200 OK`
```json
{
  "clips": [
    {"id": "clip_001", "timeline_start": 0, "timeline_end": 15.0},
    {"id": "clip_003", "timeline_start": 15.0, "timeline_end": 30.0},
    {"id": "clip_002", "timeline_start": 30.0, "timeline_end": 45.0}
  ],
  "recalculation_time_ms": 1.2
}
```

---

#### Delete Clip
```http
DELETE /projects/{project_id}/clips/{clip_id}
```

**Response:** `204 No Content`

---

### Effects

#### List Available Effects (Discovery)
```http
GET /api/v1/effects
```

Returns all registered effects from the `EffectRegistry` with parameter schemas, AI hints, and a sample filter preview generated by the Rust builders. Each effect's `build_fn` dispatches to the corresponding Rust builder for filter generation.

**Response:** `200 OK`
```json
{
  "effects": [
    {
      "effect_type": "text_overlay",
      "name": "Text Overlay",
      "description": "Add styled text overlay with position presets",
      "parameter_schema": {
        "type": "object",
        "required": ["text"],
        "properties": {
          "text": {"type": "string", "description": "Text to display"},
          "fontsize": {"type": "integer", "default": 48, "description": "Font size in pixels"},
          "fontcolor": {"type": "string", "default": "white", "description": "Text color"},
          "position": {
            "type": "string",
            "enum": ["center", "bottom_center", "top_left", "top_right", "bottom_left", "bottom_right"],
            "default": "bottom_center",
            "description": "Position preset"
          },
          "margin": {"type": "integer", "default": 10, "description": "Margin from edge in pixels"},
          "font": {"type": "string", "description": "Font family name"}
        }
      },
      "ai_hints": {
        "text": "The text content to display on screen",
        "position": "Use bottom_center for subtitles, center for titles"
      },
      "filter_preview": "drawtext=text='Sample Text':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-text_h-20"
    },
    {
      "effect_type": "speed_control",
      "name": "Speed Control",
      "description": "Change playback speed with automatic audio adjustment",
      "parameter_schema": {
        "type": "object",
        "required": ["factor"],
        "properties": {
          "factor": {"type": "number", "minimum": 0.25, "maximum": 4.0, "default": 2.0, "description": "Speed multiplier"},
          "drop_audio": {"type": "boolean", "default": false, "description": "Remove audio instead of adjusting"}
        }
      },
      "ai_hints": {
        "factor": "Values > 1 speed up, < 1 slow down. Audio is auto-adjusted via atempo chain"
      },
      "filter_preview": "setpts=0.5*PTS; atempo=2"
    },
    {
      "effect_type": "audio_mix",
      "name": "Audio Mix",
      "description": "Mix multiple audio inputs together",
      "parameter_schema": {
        "type": "object",
        "required": ["inputs"],
        "properties": {
          "inputs": {"type": "integer", "minimum": 2, "maximum": 32, "description": "Number of audio inputs"},
          "duration_mode": {"type": "string", "enum": ["longest", "shortest", "first"], "default": "longest"},
          "weights": {"type": "array", "items": {"type": "number"}, "description": "Per-input volume weights"},
          "normalize": {"type": "boolean", "default": true, "description": "Normalize output volume"}
        }
      },
      "ai_hints": {
        "inputs": "Number of audio streams to mix",
        "duration_mode": "Use 'longest' to keep all audio, 'shortest' to match shortest input"
      },
      "filter_preview": "amix=inputs=2:duration=longest:normalize=1"
    },
    {
      "effect_type": "volume",
      "name": "Volume",
      "description": "Adjust audio volume (linear or dB)",
      "parameter_schema": {
        "type": "object",
        "required": ["volume"],
        "properties": {
          "volume": {"description": "Volume level (0.0-10.0) or dB string like '-3dB'"},
          "precision": {"type": "string", "enum": ["fixed", "float", "double"], "description": "Sample precision"}
        }
      },
      "ai_hints": {
        "volume": "Use 0.0-1.0 for quieter, 1.0+ for louder, or dB strings like '-3dB'"
      },
      "filter_preview": "volume=0.8"
    },
    {
      "effect_type": "audio_fade",
      "name": "Audio Fade",
      "description": "Audio fade in or out with configurable curve",
      "parameter_schema": {
        "type": "object",
        "required": ["fade_type", "duration"],
        "properties": {
          "fade_type": {"type": "string", "enum": ["in", "out"], "description": "Fade direction"},
          "duration": {"type": "number", "minimum": 0, "description": "Fade duration in seconds"},
          "start_time": {"type": "number", "description": "Start time in seconds"},
          "curve": {"type": "string", "description": "Fade curve (tri, qsin, hsin, esin, log, etc.)"}
        }
      },
      "ai_hints": {
        "fade_type": "Use 'in' for fade-in at start, 'out' for fade-out at end",
        "curve": "tri (linear) is most common; qsin gives a smoother S-curve"
      },
      "filter_preview": "afade=t=in:d=2"
    },
    {
      "effect_type": "audio_ducking",
      "name": "Audio Ducking",
      "description": "Automatically lower background audio when speech is detected",
      "parameter_schema": {
        "type": "object",
        "properties": {
          "threshold": {"type": "number", "description": "Detection threshold"},
          "ratio": {"type": "number", "description": "Compression ratio"},
          "attack": {"type": "number", "description": "Attack time in seconds"},
          "release": {"type": "number", "description": "Release time in seconds"}
        }
      },
      "ai_hints": {
        "threshold": "Lower values = more sensitive ducking",
        "ratio": "Higher values = more aggressive volume reduction"
      },
      "filter_preview": "[speech]asplit[sc][speech_out];[music][sc]sidechaincompress=threshold=0.05:ratio=4:attack=0.01:release=0.3[ducked];[speech_out]anull"
    },
    {
      "effect_type": "video_fade",
      "name": "Video Fade",
      "description": "Video fade in or out",
      "parameter_schema": {
        "type": "object",
        "required": ["fade_type", "duration"],
        "properties": {
          "fade_type": {"type": "string", "enum": ["in", "out"], "description": "Fade direction"},
          "duration": {"type": "number", "minimum": 0, "description": "Fade duration in seconds"},
          "start_time": {"type": "number", "description": "Start time in seconds"},
          "color": {"type": "string", "default": "black", "description": "Fade color"},
          "alpha": {"type": "boolean", "default": false, "description": "Fade alpha channel instead of color"}
        }
      },
      "ai_hints": {
        "fade_type": "Use 'in' at clip start, 'out' at clip end",
        "color": "Use 'black' for standard fades, 'white' for bright transitions"
      },
      "filter_preview": "fade=t=in:d=1.5"
    },
    {
      "effect_type": "xfade",
      "name": "Crossfade (Video)",
      "description": "Video crossfade transition between clips (59 transition types)",
      "parameter_schema": {
        "type": "object",
        "required": ["transition", "duration", "offset"],
        "properties": {
          "transition": {"type": "string", "description": "Transition name (dissolve, wipeleft, circleopen, etc.)"},
          "duration": {"type": "number", "minimum": 0, "maximum": 60, "description": "Transition duration in seconds"},
          "offset": {"type": "number", "description": "Offset in seconds where transition starts"}
        }
      },
      "ai_hints": {
        "transition": "dissolve is most common; wipeleft/wiperight for directional; circleopen/circleclose for reveals"
      },
      "filter_preview": "xfade=transition=dissolve:duration=1:offset=5"
    },
    {
      "effect_type": "acrossfade",
      "name": "Crossfade (Audio)",
      "description": "Audio crossfade between clips",
      "parameter_schema": {
        "type": "object",
        "required": ["duration"],
        "properties": {
          "duration": {"type": "number", "minimum": 0, "maximum": 60, "description": "Crossfade duration in seconds"},
          "curve1": {"type": "string", "description": "Fade-out curve for first clip"},
          "curve2": {"type": "string", "description": "Fade-in curve for second clip"},
          "overlap": {"type": "boolean", "default": true, "description": "Enable overlap mode"}
        }
      },
      "ai_hints": {
        "duration": "Match this to the video xfade duration for seamless transitions",
        "curve1": "tri (linear) or qsin (smooth) are most common"
      },
      "filter_preview": "acrossfade=d=1:c1=tri:c2=tri:o=1"
    }
  ],
  "total": 9
}
```

---

#### Apply Effect to Clip
```http
POST /api/v1/projects/{project_id}/clips/{clip_id}/effects
```

Applies an effect to a clip by generating the filter string via the corresponding Rust builder and persisting the result in the clip's `effects_json` column.

**Request Body:**
```json
{
  "effect_type": "text_overlay",
  "parameters": {
    "text": "Chapter 1: Introduction",
    "fontsize": 64,
    "fontcolor": "white",
    "position": "center"
  }
}
```

**Note:** Filter string is generated by Rust core via `DrawtextBuilder`. Text is automatically sanitized for FFmpeg safety. The effect configuration is stored persistently in the clip model's `effects_json` field.

**Response:** `201 Created`
```json
{
  "effect_type": "text_overlay",
  "parameters": {
    "text": "Chapter 1: Introduction",
    "fontsize": 64,
    "fontcolor": "white",
    "position": "center"
  },
  "filter_string": "drawtext=text='Chapter 1\\: Introduction':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
}
```

**Error Responses:**
- `404`: Project or clip not found
- `400 EFFECT_NOT_FOUND`: Unknown effect type
- `400 INVALID_EFFECT_PARAMS`: Invalid parameters for the Rust builder

---

#### Apply Transition Between Clips
```http
POST /api/v1/projects/{project_id}/effects/transition
```

Applies a transition effect between two adjacent clips in the project timeline. The clips must be adjacent (target immediately follows source in timeline order). The filter string is generated by dispatching to the corresponding Rust builder via the effect registry.

**Request Body:**
```json
{
  "source_clip_id": "clip_001",
  "target_clip_id": "clip_002",
  "transition_type": "xfade",
  "parameters": {
    "transition": "dissolve",
    "duration": 1.0,
    "offset": 5.0
  }
}
```

**Note:** `transition_type` must be a registered effect in the registry (e.g., `xfade`, `acrossfade`, `video_fade`). The `source_clip_id` and `target_clip_id` must be adjacent in the project timeline. Parameters are validated against the effect's JSON Schema before filter generation.

**Response:** `201 Created`
```json
{
  "source_clip_id": "clip_001",
  "target_clip_id": "clip_002",
  "transition_type": "xfade",
  "parameters": {
    "transition": "dissolve",
    "duration": 1.0,
    "offset": 5.0
  },
  "filter_string": "xfade=transition=dissolve:duration=1:offset=5"
}
```

**Error Responses:**
- `404 NOT_FOUND`: Project or clip not found
- `400 SAME_CLIP`: source and target clip IDs are identical
- `400 EMPTY_TIMELINE`: Project timeline has no clips
- `400 NOT_ADJACENT`: Clips are not adjacent in timeline order
- `400 EFFECT_NOT_FOUND`: Transition type not registered in registry
- `400 INVALID_EFFECT_PARAMS`: Parameters fail JSON Schema validation

---

#### Preview Effect Filter
```http
POST /api/v1/effects/preview
```

Previews what filter string would be generated for an effect without applying it to a clip. Useful for testing parameter combinations and for the GUI's live filter preview.

**Request Body:**
```json
{
  "effect_type": "text_overlay",
  "parameters": {
    "text": "Hello World",
    "fontsize": 64,
    "position": "center"
  }
}
```

**Response:** `200 OK`
```json
{
  "effect_type": "text_overlay",
  "filter_string": "drawtext=text='Hello World':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
}
```

**Error Responses:**
- `400 EFFECT_NOT_FOUND`: Unknown effect type
- `400 INVALID_EFFECT_PARAMS`: Invalid parameters for the Rust builder

---

#### Update Clip Effect
```http
PATCH /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index}
```

Updates an existing effect on a clip by index. The effect type is taken from the stored effect; only parameters are updated. The filter string is regenerated by the Rust builder with the new parameters.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID |
| `clip_id` | string | Clip ID |
| `index` | int | Zero-based index into the clip's effect list |

**Request Body:**
```json
{
  "parameters": {
    "text": "Updated Title",
    "fontsize": 72,
    "position": "top_left"
  }
}
```

**Note:** The `effect_type` is not included in the request body — it is read from the existing stored effect at the given index.

**Response:** `200 OK`
```json
{
  "effect_type": "text_overlay",
  "parameters": {
    "text": "Updated Title",
    "fontsize": 72,
    "position": "top_left"
  },
  "filter_string": "drawtext=text='Updated Title':fontsize=72:fontcolor=white:x=10:y=10"
}
```

**Error Responses:**
- `404 NOT_FOUND`: Project, clip, or effect index not found
- `400 INVALID_EFFECT_PARAMS`: Invalid parameters for the effect type

---

#### Delete Clip Effect
```http
DELETE /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index}
```

Removes an effect from a clip by index.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID |
| `clip_id` | string | Clip ID |
| `index` | int | Zero-based index into the clip's effect list |

**Response:** `200 OK`
```json
{
  "index": 0,
  "deleted_effect_type": "text_overlay"
}
```

**Error Responses:**
- `404 NOT_FOUND`: Project, clip, or effect index not found

---

### Rendering

#### Start Render Job
```http
POST /render/start
```

**Request Body:**
```json
{
  "project_id": "proj_abc123",
  "output_path": "/home/user/output/video.mp4",
  "format": "mp4",
  "quality": "high",
  "hardware_accel": "auto"
}
```

**Quality Options:** `draft`, `medium`, `high`, `lossless`

**Hardware Accel Options:** `auto`, `nvenc`, `vaapi`, `qsv`, `none`

**Note:** FFmpeg command is built by Rust core. Output path is validated by Rust core.

**Response:** `202 Accepted`
```json
{
  "job_id": "job_render_001",
  "status": "queued",
  "project_id": "proj_abc123",
  "output_path": "/home/user/output/video.mp4",
  "created_at": "2024-01-15T12:00:00Z",
  "ffmpeg_command_preview": "ffmpeg -i ... -filter_complex ... output.mp4"
}
```

---

#### Get Render Status
```http
GET /render/status/{job_id}
```

**Response (Queued):** `200 OK`
```json
{
  "job_id": "job_render_001",
  "status": "queued",
  "position": 2,
  "created_at": "2024-01-15T12:00:00Z"
}
```

**Response (Running):** `200 OK`
```json
{
  "job_id": "job_render_001",
  "status": "running",
  "progress": 0.45,
  "current_frame": 1350,
  "total_frames": 3000,
  "fps": 45.2,
  "eta_seconds": 37,
  "started_at": "2024-01-15T12:00:05Z"
}
```

**Response (Completed):** `200 OK`
```json
{
  "job_id": "job_render_001",
  "status": "completed",
  "progress": 1.0,
  "output_path": "/home/user/output/video.mp4",
  "output_size": 52000000,
  "duration": 45.5,
  "render_time": 32.5,
  "completed_at": "2024-01-15T12:00:38Z"
}
```

**Response (Failed):** `200 OK`
```json
{
  "job_id": "job_render_001",
  "status": "failed",
  "error": "FFmpeg encoding error",
  "error_details": "Error while opening encoder for output stream #0:0",
  "suggestion": "Try using software encoding (hardware_accel: none)",
  "ffmpeg_command": "ffmpeg -i ... (full command for debugging)",
  "failed_at": "2024-01-15T12:00:15Z"
}
```

---

#### Cancel Render
```http
POST /render/cancel/{job_id}
```

**Response:** `200 OK`
```json
{
  "job_id": "job_render_001",
  "status": "cancelled",
  "cancelled_at": "2024-01-15T12:00:20Z"
}
```

---

#### List Render Jobs
```http
GET /render/jobs
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | all | Filter by status |
| `limit` | int | 20 | Results per page |

**Response:** `200 OK`
```json
{
  "jobs": [
    {
      "job_id": "job_render_001",
      "project_id": "proj_abc123",
      "status": "completed",
      "created_at": "2024-01-15T12:00:00Z"
    }
  ]
}
```

---

### WebSocket (Real-Time Events)

#### Connect to WebSocket
```
ws://localhost:8000/ws
```

Establishes a WebSocket connection for receiving real-time server events. The server sends a heartbeat message at a configurable interval (default 30s, set via `STOAT_WS_HEARTBEAT_INTERVAL`) to keep the connection alive.

**Event Message Schema:**
```json
{
  "type": "<event_type>",
  "payload": {},
  "correlation_id": "uuid",
  "timestamp": "2024-01-15T12:00:00.123Z"
}
```

**Event Types:**

| Type | Description | Payload |
|------|-------------|---------|
| `heartbeat` | Keep-alive signal | `{}` |
| `scan.started` | Video scan initiated | `{"path": "/media"}` |
| `scan.completed` | Scan finished | `{"scanned": 47}` |
| `project.created` | New project created | `{"project_id": "..."}` |
| `health.status` | Health check event | `{"status": "ok"}` |

---

### GUI Static Files

#### Serve Frontend
```http
GET /gui
GET /gui/{path}
```

Serves the built React frontend as static files. Configured via `STOAT_GUI_STATIC_PATH` setting (default: `gui/dist`). Uses `html=True` mode for SPA client-side routing — non-file paths return `index.html`.

Only mounted when the configured directory exists on disk.

---

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "specific_field",
      "value": "invalid_value",
      "constraint": "description of constraint"
    },
    "suggestion": "How to fix this error",
    "validated_by": "rust_core"
  }
}
```

### Error Codes

| Code | HTTP | Description | Validator |
|------|------|-------------|-----------|
| `NOT_FOUND` | 404 | Resource does not exist | Python |
| `INVALID_INPUT` | 400 | Request validation failed | Pydantic |
| `INVALID_PATH` | 400 | File path invalid or not accessible | Rust |
| `INVALID_TIME_RANGE` | 400 | In/out points invalid | Rust |
| `UNSUPPORTED_FORMAT` | 400 | File format not supported | Python |
| `EFFECT_NOT_FOUND` | 400 | Effect type does not exist | Python |
| `INVALID_EFFECT_PARAMS` | 400 | Effect parameters invalid | Rust |
| `SAME_CLIP` | 400 | Transition source and target are same clip | Python |
| `EMPTY_TIMELINE` | 400 | Project timeline has no clips | Python |
| `NOT_ADJACENT` | 400 | Transition clips are not adjacent | Python |
| `UNSAFE_INPUT` | 400 | Input contains unsafe characters | Rust |
| `RENDER_IN_PROGRESS` | 409 | Cannot modify project during render | Python |
| `FFMPEG_ERROR` | 500 | FFmpeg processing failed | Python |
| `RUST_CORE_ERROR` | 500 | Rust core operation failed | Rust |
| `INTERNAL_ERROR` | 500 | Unexpected server error | Python |

### Example Errors

**Invalid time range (validated by Rust):**
```json
{
  "error": {
    "code": "INVALID_TIME_RANGE",
    "message": "In point must be less than out point",
    "details": {
      "in_point": 25.0,
      "out_point": 10.0
    },
    "suggestion": "Set in_point to a value less than 10.0, or increase out_point",
    "validated_by": "rust_core"
  }
}
```

**Unsafe input (sanitized by Rust):**
```json
{
  "error": {
    "code": "UNSAFE_INPUT",
    "message": "Text contains characters that cannot be safely escaped for FFmpeg",
    "details": {
      "field": "text",
      "problematic_chars": ["\\x00"]
    },
    "suggestion": "Remove null characters from text input",
    "validated_by": "rust_core"
  }
}
```

**Path not found (validated by Rust):**
```json
{
  "error": {
    "code": "INVALID_PATH",
    "message": "Source file does not exist",
    "details": {
      "path": "/home/user/videos/missing.mp4"
    },
    "suggestion": "Verify the file path is correct and the file exists",
    "validated_by": "rust_core"
  }
}
```

**Invalid effect params:**
```json
{
  "error": {
    "code": "INVALID_EFFECT_PARAMS",
    "message": "Effect parameter 'speed' out of range",
    "details": {
      "parameter": "speed",
      "value": 10.0,
      "min": 0.25,
      "max": 4.0
    },
    "suggestion": "Set speed to a value between 0.25 and 4.0",
    "validated_by": "rust_core"
  }
}
```

---

## AI Integration Examples

### Natural Language to API

**User:** "Add a title 'Summer Vacation' that fades in over 2 seconds at the start of the first clip"

**AI Translation:**
```http
POST /api/v1/projects/proj_001/clips/clip_001/effects
{
  "effect_type": "text_overlay",
  "parameters": {
    "text": "Summer Vacation",
    "fontsize": 48,
    "fontcolor": "white",
    "position": "center"
  }
}
```

**Response includes generated filter string:**
```json
{
  "effect_type": "text_overlay",
  "parameters": {"text": "Summer Vacation", "fontsize": 48, "fontcolor": "white", "position": "center"},
  "filter_string": "drawtext=text='Summer Vacation':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
}
```

---

**User:** "Add a dissolve transition between the first and second clips"

**AI Translation:**
```http
POST /api/v1/projects/proj_001/effects/transition
{
  "source_clip_id": "clip_001",
  "target_clip_id": "clip_002",
  "transition_type": "xfade",
  "parameters": {
    "transition": "dissolve",
    "duration": 1.0,
    "offset": 14.0
  }
}
```

**Response includes generated filter string:**
```json
{
  "source_clip_id": "clip_001",
  "target_clip_id": "clip_002",
  "transition_type": "xfade",
  "parameters": {"transition": "dissolve", "duration": 1.0, "offset": 14.0},
  "filter_string": "xfade=transition=dissolve:duration=1:offset=14"
}
```

---

**User:** "Speed up the second clip to 1.5x"

**AI Translation:**
```http
POST /api/v1/projects/proj_001/clips/clip_002/effects
{
  "effect_type": "speed_control",
  "parameters": {
    "factor": 1.5
  }
}
```

---

**User:** "Export the project in high quality"

**AI Translation:**
```http
POST /render/start
{
  "project_id": "proj_001",
  "output_path": "/home/user/output/summer_vacation.mp4",
  "quality": "high"
}
```

---

### Debugging with Filter Strings

When AI or user needs to debug an effect, the `filter_string` field in the apply response shows exactly what FFmpeg filter will be applied:

```http
POST /api/v1/projects/proj_001/clips/clip_001/effects
{
  "effect_type": "text_overlay",
  "parameters": {
    "text": "Hello: World!",
    "position": "center"
  }
}
```

**Response:**
```json
{
  "effect_type": "text_overlay",
  "parameters": {"text": "Hello: World!", "position": "center"},
  "filter_string": "drawtext=text='Hello\\: World!':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
}
```

Note how special characters (`:`) are automatically escaped by the Rust `DrawtextBuilder`. The discovery endpoint (`GET /api/v1/effects`) also includes a `filter_preview` field showing a sample output from each Rust builder.

---

### Batch Operations

For AI-driven batch operations, use multiple sequential API calls:

```python
# AI adds multiple clips
clips = [
    {"source": "clip1.mp4", "in_point": 0, "out_point": 10},
    {"source": "clip2.mp4", "in_point": 5, "out_point": 15},
    {"source": "clip3.mp4", "in_point": 0, "out_point": 20},
]

for clip in clips:
    response = client.post(f"/projects/{project_id}/clips", json=clip)
    # Clips automatically positioned sequentially
    # Timeline recalculated by Rust core after each addition
```

---

## OpenAPI Specification

The full OpenAPI 3.0 specification is available at:
```
GET /openapi.json
```

Interactive documentation (Swagger UI):
```
GET /docs
```

Alternative documentation (ReDoc):
```
GET /redoc
```

**Note:** OpenAPI schema is automatically generated by FastAPI from Pydantic models. This enables AI agents to discover the API programmatically and understand all available operations.

---

## Known Limitations

### SPA Fallback for GUI Routes

The GUI is served as static files via FastAPI's `StaticFiles` mount with `html=True`. While this serves `index.html` for non-file paths under `/gui`, direct URL access to client-side routes like `/gui/effects` may return a 404 if the server's static file handler does not find a matching file.

**Workaround:** Navigate to `/gui` first, then use client-side navigation (clicking links in the app) to reach sub-routes like `/gui/effects`, `/gui/library`, or `/gui/projects`. The React Router handles routing correctly once the SPA is loaded.

---

## Performance Notes

| Operation | Typical Latency | Component |
|-----------|-----------------|-----------|
| Filter generation | <1ms | Rust core |
| Timeline calculation (100 clips) | <5ms | Rust core |
| Path validation | <0.1ms | Rust core |
| Effect parameter validation | <0.5ms | Rust core |
| API response (p95) | <200ms | Python/FastAPI |
| Health check | <100ms | Python |

The Rust core handles all compute-intensive operations, ensuring consistent low latency for filter generation and timeline calculations regardless of project complexity.
