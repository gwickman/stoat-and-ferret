# Phase 3: API Endpoints

## Overview

Phase 3 adds composition endpoints for multi-clip timelines, layout operations, audio mixing, and batch processing. All endpoints follow existing REST conventions (see `05-api-specification.md`): nested resources, JSON:API-style errors, and correlation ID middleware.

## Timeline Endpoints

### Create/Update Timeline for Project

```http
PUT /api/v1/projects/{project_id}/timeline
Content-Type: application/json

{
  "tracks": [
    {"id": "track-v1", "track_type": "video", "label": "Main Video", "z_index": 0},
    {"id": "track-a1", "track_type": "audio", "label": "Audio", "z_index": 0}
  ]
}

Response 200:
{
  "project_id": "proj_abc123",
  "tracks": [...],
  "clips": [],
  "duration": 0.0,
  "version": 2
}
```

### Get Timeline

```http
GET /api/v1/projects/{project_id}/timeline

Response 200:
{
  "project_id": "proj_abc123",
  "tracks": [...],
  "clips": [...],
  "duration": 45.5,
  "version": 3
}
```

### Add Clip to Track

```http
POST /api/v1/projects/{project_id}/timeline/clips
Content-Type: application/json

{
  "track_id": "track-v1",
  "source_video_id": 1,
  "in_point": 10.0,
  "out_point": 25.0,
  "timeline_start": 0.0
}

Response 201:
{
  "id": "clip_xyz789",
  "track_id": "track-v1",
  "source_video_id": 1,
  "in_point": 10.0,
  "out_point": 25.0,
  "timeline_start": 0.0,
  "timeline_end": 15.0,
  "effects": [],
  "transition_in": null,
  "transition_out": null
}
```

### Move Clip on Timeline

```http
PATCH /api/v1/projects/{project_id}/timeline/clips/{clip_id}
Content-Type: application/json

{
  "timeline_start": 5.0,
  "track_id": "track-v2"
}

Response 200:
{ ... updated clip ... }
```

## Transition Endpoints

Existing transition endpoints in `effects.py` remain. Phase 3 adds timeline-aware transition application:

### Apply Timeline Transition

```http
POST /api/v1/projects/{project_id}/timeline/transitions
Content-Type: application/json

{
  "source_clip_id": "clip_001",
  "target_clip_id": "clip_002",
  "transition_type": "xfade",
  "duration": 1.0,
  "parameters": {"style": "fade"}
}

Response 201:
{
  "source_clip_id": "clip_001",
  "target_clip_id": "clip_002",
  "transition_type": "xfade",
  "duration": 1.0,
  "parameters": {"style": "fade"},
  "filter_string": "xfade=transition=fade:duration=1:offset=14",
  "timeline_offset": 14.0
}
```

### Remove Timeline Transition

```http
DELETE /api/v1/projects/{project_id}/timeline/transitions/{transition_id}

Response 200:
{"deleted": true, "transition_id": "..."}
```

## Layout / Composition Endpoints

### Apply Layout to Timeline

```http
POST /api/v1/projects/{project_id}/compose/layout
Content-Type: application/json

{
  "preset": "side_by_side"
}

Response 200:
{
  "preset": "side_by_side",
  "positions": [
    {"x": 0.0, "y": 0.0, "width": 0.5, "height": 1.0, "z_index": 0},
    {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0, "z_index": 0}
  ],
  "filter_preview": "...[scale]...[overlay]..."
}
```

### Custom Layout

```http
POST /api/v1/projects/{project_id}/compose/layout
Content-Type: application/json

{
  "positions": [
    {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0, "z_index": 0},
    {"x": 0.7, "y": 0.05, "width": 0.25, "height": 0.25, "z_index": 1}
  ]
}

Response 200:
{
  "preset": null,
  "positions": [...],
  "filter_preview": "..."
}
```

### List Layout Presets

```http
GET /api/v1/compose/presets

Response 200:
{
  "presets": [
    {
      "id": "pip_top_right",
      "name": "Picture-in-Picture (Top Right)",
      "description": "Main video with small overlay in top-right corner",
      "ai_hint": "Use for commentary overlay or webcam-style PIP",
      "min_inputs": 2,
      "max_inputs": 2
    },
    {
      "id": "side_by_side",
      "name": "Side by Side",
      "description": "Two videos displayed side by side",
      "ai_hint": "Use for comparison or reaction-style videos",
      "min_inputs": 2,
      "max_inputs": 2
    },
    {
      "id": "grid_2x2",
      "name": "2x2 Grid",
      "description": "Four videos in a 2x2 grid layout",
      "ai_hint": "Use for multi-camera or surveillance-style display",
      "min_inputs": 4,
      "max_inputs": 4
    }
  ]
}
```

## Audio Mixing Endpoints

### Set Audio Mix for Project

```http
PUT /api/v1/projects/{project_id}/audio/mix
Content-Type: application/json

{
  "tracks": [
    {"track_id": "track-a1", "volume": 1.0, "fade_in": 0.5, "fade_out": 0.5},
    {"track_id": "track-a2", "volume": 0.3, "fade_in": 0.0, "fade_out": 1.0}
  ],
  "master_volume": 0.9,
  "normalize": false
}

Response 200:
{
  "tracks": [...],
  "master_volume": 0.9,
  "normalize": false,
  "filter_preview": "amix=inputs=2:duration=longest,volume=0.9"
}
```

### Preview Audio Mix Filter

```http
POST /api/v1/audio/mix/preview
Content-Type: application/json

{
  "tracks": [
    {"track_id": "track-a1", "volume": 1.0},
    {"track_id": "track-a2", "volume": 0.5}
  ],
  "master_volume": 1.0
}

Response 200:
{
  "filter_string": "amix=inputs=2:duration=longest,volume=1.0"
}
```

## Batch Processing Endpoints

### Start Batch Render

```http
POST /api/v1/render/batch
Content-Type: application/json

{
  "jobs": [
    {"project_id": "proj_001", "output_path": "/output/video1.mp4", "quality": "high"},
    {"project_id": "proj_002", "output_path": "/output/video2.mp4", "quality": "medium"}
  ],
  "parallel": 2
}

Response 202:
{
  "batch_id": "batch_abc123",
  "total": 2,
  "completed": 0,
  "failed": 0,
  "in_progress": 0,
  "jobs": [
    {"job_id": "job_001", "status": "queued", "project_id": "proj_001"},
    {"job_id": "job_002", "status": "queued", "project_id": "proj_002"}
  ]
}
```

### Get Batch Status

```http
GET /api/v1/render/batch/{batch_id}

Response 200:
{
  "batch_id": "batch_abc123",
  "total": 2,
  "completed": 1,
  "failed": 0,
  "in_progress": 1,
  "overall_progress": 0.65,
  "jobs": [
    {"job_id": "job_001", "status": "complete", "progress": 1.0},
    {"job_id": "job_002", "status": "running", "progress": 0.3}
  ]
}
```

## Project Version Endpoints

### List Project Versions

```http
GET /api/v1/projects/{project_id}/versions?limit=10

Response 200:
{
  "versions": [
    {"version": 3, "timestamp": "2026-03-09T10:30:00Z", "checksum": "abc123"},
    {"version": 2, "timestamp": "2026-03-09T10:15:00Z", "checksum": "def456"}
  ],
  "current_version": 3
}
```

### Restore Project Version

```http
POST /api/v1/projects/{project_id}/versions/{version}/restore

Response 200:
{
  "project_id": "proj_abc123",
  "restored_version": 2,
  "new_version": 4,
  "message": "Restored to version 2 (saved as version 4)"
}
```

## Error Cases

All endpoints return structured errors per existing pattern:

```json
{
  "error": {
    "code": "INVALID_LAYOUT_POSITION",
    "category": "validation",
    "message": "Layout position x=1.5 is outside valid range [0.0, 1.0]",
    "details": {"field": "x", "value": 1.5, "min": 0.0, "max": 1.0},
    "suggestion": "Set x to a value between 0.0 and 1.0",
    "correlation_id": "req_xyz789"
  }
}
```

| Error Code | HTTP Status | Condition |
|-----------|------------|-----------|
| `INVALID_LAYOUT_POSITION` | 422 | Position coordinates outside 0.0-1.0 |
| `CLIPS_NOT_ADJACENT` | 422 | Transition between non-adjacent clips |
| `TRACK_NOT_FOUND` | 404 | Referenced track doesn't exist |
| `INSUFFICIENT_INPUTS` | 422 | Layout preset requires more inputs than provided |
| `INVALID_AUDIO_VOLUME` | 422 | Volume outside 0.0-2.0 range |
| `PROJECT_VERSION_NOT_FOUND` | 404 | Requested version doesn't exist |
| `BATCH_JOB_LIMIT_EXCEEDED` | 422 | Too many jobs in batch request |

## New Router Files

```
src/stoat_ferret/api/routers/
├── timeline.py       # NEW — timeline CRUD, clip positioning
├── compose.py        # NEW — layout presets, custom layouts
├── audio.py          # NEW — audio mix configuration
├── batch.py          # NEW — batch render operations
├── versions.py       # NEW — project version history
├── projects.py       # EXTEND — link to timeline
├── effects.py        # existing (no changes)
├── videos.py         # existing (no changes)
├── jobs.py           # existing (no changes)
├── health.py         # existing (no changes)
└── ...
```
