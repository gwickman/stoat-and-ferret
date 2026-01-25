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

#### Scan Directory
```http
POST /videos/scan
```

**Request Body:**
```json
{
  "path": "/home/user/videos",
  "recursive": true
}
```

**Note:** Path validation is performed by Rust core for security.

**Response:** `200 OK`
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

#### List Available Effects
```http
GET /effects
```

**Response:** `200 OK`
```json
{
  "effects": [
    {
      "type": "text_overlay",
      "name": "Text Overlay",
      "description": "Add text with optional fade animation",
      "category": "overlay",
      "ai_hint": "Use this to add titles, captions, or labels to video",
      "rust_generated": true,
      "parameters": {
        "text": {
          "type": "string",
          "required": true,
          "description": "Text to display"
        },
        "position": {
          "type": "enum",
          "values": ["center", "top", "bottom", "top_left", "top_right", "bottom_left", "bottom_right", "custom"],
          "default": "center",
          "description": "Text position on screen"
        },
        "x": {
          "type": "integer",
          "description": "Custom X position (only when position=custom)"
        },
        "y": {
          "type": "integer",
          "description": "Custom Y position (only when position=custom)"
        },
        "font_size": {
          "type": "integer",
          "min": 8,
          "max": 500,
          "default": 48,
          "description": "Font size in pixels"
        },
        "font_color": {
          "type": "string",
          "format": "color",
          "default": "white",
          "description": "Text color (name or hex)"
        },
        "font_family": {
          "type": "string",
          "default": "sans-serif",
          "description": "Font family name"
        },
        "start": {
          "type": "number",
          "min": 0,
          "default": 0,
          "description": "Start time relative to clip (seconds)"
        },
        "duration": {
          "type": "number",
          "min": 0,
          "description": "Duration in seconds (null = until clip end)"
        },
        "fade_in": {
          "type": "number",
          "min": 0,
          "default": 0,
          "description": "Fade in duration (seconds)"
        },
        "fade_out": {
          "type": "number",
          "min": 0,
          "default": 0,
          "description": "Fade out duration (seconds)"
        }
      }
    },
    {
      "type": "speed",
      "name": "Speed Control",
      "description": "Change playback speed of clip",
      "category": "time",
      "ai_hint": "Use this to speed up or slow down video. Values >1 speed up, <1 slow down",
      "rust_generated": true,
      "parameters": {
        "speed": {
          "type": "number",
          "min": 0.25,
          "max": 4.0,
          "default": 1.0,
          "description": "Speed multiplier (2.0 = 2x faster, 0.5 = half speed)"
        },
        "audio": {
          "type": "enum",
          "values": ["adjust", "remove", "keep"],
          "default": "adjust",
          "description": "How to handle audio: adjust pitch-corrected, remove, or keep original pitch"
        }
      }
    },
    {
      "type": "fade",
      "name": "Fade Effect",
      "description": "Add fade in or fade out to clip",
      "category": "transition",
      "ai_hint": "Use this for smooth transitions at the start or end of clips",
      "rust_generated": true,
      "parameters": {
        "type": {
          "type": "enum",
          "values": ["in", "out", "both"],
          "default": "both",
          "description": "Fade type"
        },
        "duration": {
          "type": "number",
          "min": 0.1,
          "max": 10.0,
          "default": 1.0,
          "description": "Fade duration in seconds"
        },
        "color": {
          "type": "string",
          "format": "color",
          "default": "black",
          "description": "Fade to/from color"
        }
      }
    }
  ],
  "rust_core_version": "0.1.0"
}
```

---

#### Get Effect Schema
```http
GET /effects/{effect_type}/schema
```

**Response:** `200 OK`
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "TextOverlayEffect",
  "required": ["text"],
  "properties": {
    "text": {"type": "string"},
    "position": {"type": "string", "enum": ["center", "top", "bottom", "..."]},
    "font_size": {"type": "integer", "minimum": 8, "maximum": 500, "default": 48}
  }
}
```

---

#### Add Effect to Clip
```http
POST /projects/{project_id}/clips/{clip_id}/effects
```

**Request Body:**
```json
{
  "type": "text_overlay",
  "params": {
    "text": "Chapter 1: Introduction",
    "position": "center",
    "font_size": 64,
    "font_color": "white",
    "start": 0,
    "duration": 4,
    "fade_in": 1.0,
    "fade_out": 0.5
  }
}
```

**Note:** Filter string is generated by Rust core. Text is automatically sanitized for FFmpeg safety.

**Response:** `201 Created`
```json
{
  "id": "effect_001",
  "type": "text_overlay",
  "params": {
    "text": "Chapter 1: Introduction",
    "position": "center",
    "font_size": 64,
    "font_color": "white",
    "start": 0,
    "duration": 4,
    "fade_in": 1.0,
    "fade_out": 0.5
  },
  "filter_preview": "drawtext=text='Chapter 1\\: Introduction':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,4)':alpha='if(lt(t,1),t/1,if(gt(t,3.5),1-(t-3.5)/0.5,1))'",
  "generated_by": "rust_core",
  "generation_time_ms": 0.3
}
```

---

#### Preview Effect Filter
```http
POST /effects/preview
```

Preview what filter string would be generated without applying to a clip.

**Request Body:**
```json
{
  "type": "text_overlay",
  "params": {
    "text": "Test Title",
    "position": "bottom",
    "font_size": 48
  }
}
```

**Response:** `200 OK`
```json
{
  "filter_string": "drawtext=text='Test Title':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-text_h-50",
  "params_validated": true,
  "sanitized_params": {
    "text": "Test Title"
  },
  "generation_time_ms": 0.2
}
```

---

#### Update Effect
```http
PATCH /projects/{project_id}/clips/{clip_id}/effects/{effect_id}
```

**Request Body:**
```json
{
  "params": {
    "text": "Chapter 1",
    "font_size": 72
  }
}
```

**Response:** `200 OK`
```json
{
  "id": "effect_001",
  "type": "text_overlay",
  "params": {
    "text": "Chapter 1",
    "position": "center",
    "font_size": 72,
    "font_color": "white",
    "start": 0,
    "duration": 4,
    "fade_in": 1.0,
    "fade_out": 0.5
  },
  "filter_preview": "drawtext=text='Chapter 1':fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,4)':alpha='if(lt(t,1),t/1,if(gt(t,3.5),1-(t-3.5)/0.5,1))'"
}
```

---

#### Delete Effect
```http
DELETE /projects/{project_id}/clips/{clip_id}/effects/{effect_id}
```

**Response:** `204 No Content`

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
POST /projects/proj_001/clips/clip_001/effects
{
  "type": "text_overlay",
  "params": {
    "text": "Summer Vacation",
    "position": "center",
    "start": 0,
    "duration": 5,
    "fade_in": 2.0,
    "fade_out": 0.5
  }
}
```

**Response includes filter preview:**
```json
{
  "id": "effect_001",
  "type": "text_overlay",
  "params": {...},
  "filter_preview": "drawtext=text='Summer Vacation':..."
}
```

---

**User:** "Speed up the second clip to 1.5x"

**AI Translation:**
```http
POST /projects/proj_001/clips/clip_002/effects
{
  "type": "speed",
  "params": {
    "speed": 1.5,
    "audio": "adjust"
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

### Debugging with Filter Preview

When AI or user needs to debug an effect, the `filter_preview` field shows exactly what FFmpeg filter will be applied:

```http
POST /effects/preview
{
  "type": "text_overlay",
  "params": {
    "text": "Hello: World!",
    "position": "center"
  }
}
```

**Response:**
```json
{
  "filter_string": "drawtext=text='Hello\\: World\\!':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
  "params_validated": true,
  "sanitized_params": {
    "text": "Hello\\: World\\!"
  }
}
```

Note how special characters (`:`, `!`) are automatically escaped by the Rust core.

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
