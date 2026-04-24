# API Usage Examples

Canonical request/response flows for the five primary workflows an operator
or agent drives against the stoat-and-ferret HTTP API. Every `curl` command
below was run end-to-end against a locally-built server (v0.3.0, core 0.1.0,
git SHA `8bb450d`) on 2026-04-24 and the snippets show real response bodies
with only IDs and absolute paths anonymised. The process that produced this
evidence is described in [`docs/design/VALIDATION_FRAMEWORK.md`](../design/VALIDATION_FRAMEWORK.md).

For orientation before diving into examples, see:

- [`02_api-overview.md`](02_api-overview.md) — conceptual model of the API surface.
- [`ai-integration-patterns.md`](ai-integration-patterns.md) — request shapes tuned for LLM agents (discovery, chaining, error recovery).
- Live OpenAPI docs at `http://localhost:8765/docs` — every endpoint, request, and response model.

## Conventions

- **Base URL.** All requests assume `http://localhost:8765` (override via `STOAT_API_HOST` / `STOAT_API_PORT`).
- **IDs.** `proj-xxxxxxxx`, `clip-xxxxxxxx`, `vid-xxxxxxxx`, `job-xxxxxxxx`, `batch-xxxxxxxx` stand in for real UUIDs.
- **Timestamps.** ISO 8601 UTC. Sample responses show the real timestamp format (`2026-04-24T07:23:49.174861Z`).
- **Error envelope.** Errors return `{"detail": {"code": "SOME_CODE", "message": "..."}}` for business logic failures and `{"detail": [...]}` for Pydantic request-validation failures.
- **Long-poll pattern (BL-277).** Asynchronous jobs expose `GET /api/v1/jobs/{job_id}/wait?timeout=N` which blocks up to `N` seconds (1 ≤ N ≤ 3600) and returns HTTP 408 `JOB_WAIT_TIMEOUT` when the deadline passes without reaching a terminal state. Terminal states are `complete`, `failed`, `timeout`, `cancelled`; see `src/stoat_ferret/api/routers/jobs.py`. Callers may resume waiting by calling `/wait` again.
- **WebSocket notifications.** Every state change documented below also publishes a `/ws` event (see `docs/design/Phase 06 Design/` and the WebSocket replay pattern in `FRAMEWORK_CONTEXT.md` — subscribers can replay missed events by supplying the last `event_id` via the `Last-Event-ID` header on reconnect).

## Health check first

Confirm the server is reachable before running any workflow. `/health/ready`
reports per-subsystem status and is safe to call repeatedly.

```bash
curl -s http://localhost:8765/health/ready
```

```json
{
  "ready": true,
  "status": "degraded",
  "app_version": "0.3.0",
  "sqlite_version": "3.50.4",
  "core_version": "stoat_ferret_core OK",
  "ws_buffer_utilization": 0.0,
  "uptime_seconds": 367.17,
  "checks": {
    "database": {"status": "ok", "latency_ms": 0.3, "version": "3.50.4"},
    "ffmpeg": {"status": "ok", "version": "8.0.1-full_build-www.gyan.dev"},
    "rust_core": {"status": "ok", "version": "stoat_ferret_core OK"},
    "filesystem": {"status": "ok"},
    "preview": {"status": "ok", "active_sessions": 0, "cache_healthy": true},
    "proxy": {"status": "degraded", "proxy_dir_writable": false},
    "render": {"status": "ok", "encoder_available": true, "active_jobs": 0}
  }
}
```

`ready: true` with `status: "degraded"` is a healthy-enough condition: an
individual subsystem has reduced capability but the API serves requests.

---

## Workflow 1: Library scan

Index a directory of video files, wait for the background job to finish,
then page through the results.

**Endpoint chain**

1. `POST /api/v1/videos/scan` — enqueue a scan job.
2. `GET /api/v1/jobs/{job_id}/wait?timeout=30` — block until the job reaches a terminal state.
3. `GET /api/v1/videos?limit=20&offset=0` — list the catalogued videos.

### 1.1 Submit the scan

The request body expects a platform-native directory `path`. On Windows
forward slashes work; on POSIX use the native path. Optional `recursive`
defaults to `false`.

```bash
curl -s -X POST http://localhost:8765/api/v1/videos/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "C:/Users/you/videos", "recursive": false}'
```

**Response — 202 Accepted:**

```json
{"job_id": "981c5389-01ba-4f35-a078-72c9a999a756"}
```

**Failure modes:**

| HTTP | `detail.code` | Meaning |
|------|---------------|---------|
| 400 | `INVALID_PATH` | `path` is missing or not a directory. |
| 403 | `PATH_NOT_ALLOWED` | `STOAT_ALLOWED_SCAN_ROOTS` is set and the path is outside it. |
| 422 | (Pydantic) | Body missing `path` or wrong types. |

### 1.2 Wait for completion (long-poll)

```bash
curl -s "http://localhost:8765/api/v1/jobs/981c5389-01ba-4f35-a078-72c9a999a756/wait?timeout=30"
```

**Response — 200 OK (terminal):**

```json
{
  "job_id": "981c5389-01ba-4f35-a078-72c9a999a756",
  "status": "complete",
  "progress": 1.0,
  "result": {"scanned": 6, "new": 6, "updated": 0, "skipped": 0, "errors": []},
  "error": null
}
```

If the job is still running after `timeout` seconds the server returns
HTTP 408 with `{"detail": {"code": "JOB_WAIT_TIMEOUT", ...}}`. The job
keeps running server-side — call `/wait` again to resume waiting. For
point-in-time polling without blocking, use `GET /api/v1/jobs/{job_id}`.

### 1.3 List the results

```bash
curl -s "http://localhost:8765/api/v1/videos?limit=5"
```

**Response (truncated to one video):**

```json
{
  "videos": [
    {
      "id": "af19b563-7a5e-4a09-97ca-3f8c74062956",
      "path": "C:\\Users\\you\\videos\\running2.mp4",
      "filename": "running2.mp4",
      "duration_frames": 669,
      "frame_rate_numerator": 30000,
      "frame_rate_denominator": 1001,
      "width": 960,
      "height": 540,
      "video_codec": "h264",
      "audio_codec": "aac",
      "file_size": 5177062,
      "thumbnail_path": "data\\thumbnails\\af19b563-7a5e-4a09-97ca-3f8c74062956.jpg",
      "created_at": "2026-04-24T07:23:49.174861Z",
      "updated_at": "2026-04-24T07:23:49.174863Z"
    }
  ],
  "total": 6,
  "limit": 5,
  "offset": 0
}
```

Frame rate is returned as a rational (`numerator / denominator`) so NTSC
fractional rates are preserved exactly. `duration_frames` — not seconds —
is the canonical duration unit used by clip in/out points.

---

## Workflow 2: Project creation

Build a project, add a clip that references a scanned video, then read
the project back.

**Endpoint chain**

1. `POST /api/v1/projects` — create a project.
2. `POST /api/v1/projects/{project_id}/clips` — add a clip.
3. `GET /api/v1/projects/{project_id}` — read project metadata.
4. `GET /api/v1/projects/{project_id}/clips` — list clips (with any attached effects).

### 2.1 Create the project

```bash
curl -s -X POST http://localhost:8765/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Tutorial Project", "output_width": 1920, "output_height": 1080, "output_fps": 30.0}'
```

**Response — 201 Created:**

```json
{
  "id": "cad33e49-799e-4bcf-9bbe-839301b95551",
  "name": "Tutorial Project",
  "output_width": 1920,
  "output_height": 1080,
  "output_fps": 30,
  "created_at": "2026-04-24T07:24:01.979424Z",
  "updated_at": "2026-04-24T07:24:01.979424Z"
}
```

### 2.2 Add a clip

`in_point` / `out_point` are **frame indices** into the source video
(integers, 0-based). `timeline_position` is the clip's starting frame on
the project timeline. The server validates the clip via the Rust core
(reachable file, non-empty duration, in/out within bounds).

```bash
curl -s -X POST \
  http://localhost:8765/api/v1/projects/cad33e49-799e-4bcf-9bbe-839301b95551/clips \
  -H "Content-Type: application/json" \
  -d '{
        "source_video_id": "af19b563-7a5e-4a09-97ca-3f8c74062956",
        "in_point": 0,
        "out_point": 300,
        "timeline_position": 0
      }'
```

**Response — 201 Created:**

```json
{
  "id": "9d06e177-e097-49a9-be73-2f5d96efa722",
  "project_id": "cad33e49-799e-4bcf-9bbe-839301b95551",
  "source_video_id": "af19b563-7a5e-4a09-97ca-3f8c74062956",
  "in_point": 0,
  "out_point": 300,
  "timeline_position": 0,
  "effects": null,
  "created_at": "2026-04-24T07:24:09.572910Z",
  "updated_at": "2026-04-24T07:24:09.572910Z"
}
```

**Failure modes:**

| HTTP | `detail.code` | Meaning |
|------|---------------|---------|
| 404 | `NOT_FOUND` | Project or `source_video_id` does not exist. |
| 400 | `VALIDATION_ERROR` | Rust core rejected the clip (e.g., out-of-range in/out, missing source file). |

### 2.3 Read the project

```bash
curl -s http://localhost:8765/api/v1/projects/cad33e49-799e-4bcf-9bbe-839301b95551
```

```json
{
  "id": "cad33e49-799e-4bcf-9bbe-839301b95551",
  "name": "Tutorial Project",
  "output_width": 1920,
  "output_height": 1080,
  "output_fps": 30,
  "created_at": "2026-04-24T07:24:01.979424Z",
  "updated_at": "2026-04-24T07:24:01.979424Z"
}
```

Project metadata is stable until edits; clips and effects live under
`/clips` (see 2.4 below) and are fetched separately to avoid returning a
large object graph on every read.

### 2.4 List clips

```bash
curl -s \
  http://localhost:8765/api/v1/projects/cad33e49-799e-4bcf-9bbe-839301b95551/clips
```

After Workflow 3 is run, the same endpoint surfaces the attached
effects inline (see 3.3).

---

## Workflow 3: Effect application

Discover available effects, apply one to a clip, and verify it lands on the
clip record.

**Endpoint chain**

1. `GET /api/v1/effects` — list effects with JSON-schema parameters and AI hints.
2. `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` — apply an effect.
3. `GET /api/v1/projects/{project_id}/clips` — confirm attachment and inspect the generated filter string.

### 3.1 Discover effects

```bash
curl -s http://localhost:8765/api/v1/effects
```

The full response is a list of effect descriptors; the nine effect types
exposed today are `text_overlay`, `speed_control`, `audio_mix`, `volume`,
`audio_fade`, `audio_ducking`, `video_fade`, `xfade`, `acrossfade`. Each
descriptor carries the JSON Schema under `parameter_schema` plus AI-facing
`ai_hints`, which are the two fields a model needs in order to fabricate
a correct `parameters` payload.

Truncated excerpt for `text_overlay`:

```json
{
  "effect_type": "text_overlay",
  "name": "Text Overlay",
  "description": "Add text overlays to video with customizable font, position, and styling.",
  "parameter_schema": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "The text to display"},
      "fontsize": {"type": "integer", "minimum": 8, "maximum": 256, "default": 48},
      "fontcolor": {"type": "string", "default": "white"},
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
    "fontsize": "Font size in pixels, typical range 12-72",
    "fontcolor": "Color name (white, yellow) or hex (#FF0000), append @0.5 for transparency",
    "position": "Where to place the text on screen",
    "margin": "Distance from screen edge in pixels, typical range 5-50",
    "font": "Fontconfig font name (e.g., 'monospace', 'Sans', 'Serif')"
  }
}
```

For the `{resource}` schema discovery endpoint (`GET /api/v1/schema/{resource}`)
see the effects guide at [`04_effects-guide.md`](04_effects-guide.md#schema-endpoint).

### 3.2 Apply the effect

`effect_type` must match one of the values from 3.1. `parameters` must
validate against the effect's `parameter_schema`.

```bash
curl -s -X POST \
  http://localhost:8765/api/v1/projects/cad33e49-799e-4bcf-9bbe-839301b95551/clips/9d06e177-e097-49a9-be73-2f5d96efa722/effects \
  -H "Content-Type: application/json" \
  -d '{
        "effect_type": "text_overlay",
        "parameters": {"text": "Hello World", "fontsize": 64, "position": "bottom_center"}
      }'
```

**Response — 200 OK:**

```json
{
  "effect_type": "text_overlay",
  "parameters": {"text": "Hello World", "fontsize": 64, "position": "bottom_center"},
  "filter_string": "drawtext=text=Hello World:fontsize=64:fontcolor=black:x=(w-text_w)/2:y=h-text_h-10"
}
```

`filter_string` is the literal FFmpeg filter the render pipeline will use.
Surfacing it in the API response is a deliberate transparency decision
(see `docs/design/02-architecture.md`).

**Failure modes:**

| HTTP | `detail.code` | Meaning |
|------|---------------|---------|
| 404 | `EFFECT_NOT_FOUND` | `effect_type` is not in the discovery list (e.g., `blur` is **not** a supported effect). |
| 404 | `NOT_FOUND` | Project or clip does not exist. |
| 422 | (Pydantic / schema) | `parameters` missing required fields or out of range. |

### 3.3 Confirm the attached effect

Re-list the clips; effects are now embedded in the response.

```bash
curl -s \
  http://localhost:8765/api/v1/projects/cad33e49-799e-4bcf-9bbe-839301b95551/clips
```

```json
{
  "clips": [
    {
      "id": "9d06e177-e097-49a9-be73-2f5d96efa722",
      "project_id": "cad33e49-799e-4bcf-9bbe-839301b95551",
      "source_video_id": "af19b563-7a5e-4a09-97ca-3f8c74062956",
      "in_point": 0,
      "out_point": 300,
      "timeline_position": 0,
      "effects": [
        {
          "effect_type": "text_overlay",
          "parameters": {"text": "Hello World", "fontsize": 64, "position": "bottom_center"},
          "filter_string": "drawtext=text=Hello World:fontsize=64:fontcolor=black:x=(w-text_w)/2:y=h-text_h-10"
        }
      ],
      "created_at": "2026-04-24T07:24:09.572910Z",
      "updated_at": "2026-04-24T07:24:49.587520Z"
    }
  ],
  "total": 1
}
```

Apply another effect on the same clip to chain them; filter strings are
composed in submission order during render. To remove or edit an effect,
use `DELETE` / `PATCH` against `/clips/{clip_id}/effects/{index}`.

---

## Workflow 4: Render job

Submit a render, inspect queue state, track status, and — if needed —
cancel it.

> **Operational note.** The HTTP layer enqueues render jobs and exposes
> full status/cancel/retry control, but the background render worker that
> dequeues and invokes FFmpeg is a separate service that must be running
> for a job to transition past `queued`. In a bare `python -m
> stoat_ferret.api` process, jobs will remain in `queued` until the
> worker service starts or a caller explicitly drives `RenderService.run_job`.
> See [`07_rendering-guide.md`](07_rendering-guide.md) and the runbook
> for worker wiring.

**Endpoint chain**

1. `POST /api/v1/render` — submit the job.
2. `GET /api/v1/render/queue` — check queue depth, capacity, disk headroom.
3. `GET /api/v1/render/{job_id}` — point-in-time status.
4. `POST /api/v1/render/{job_id}/cancel` — cancel while `queued` or `running`.

### 4.1 Submit

```bash
curl -s -X POST http://localhost:8765/api/v1/render \
  -H "Content-Type: application/json" \
  -d '{
        "project_id": "cad33e49-799e-4bcf-9bbe-839301b95551",
        "output_format": "mp4",
        "quality_preset": "standard",
        "render_plan": "{}"
      }'
```

**Response — 201 Created:**

```json
{
  "id": "11b21570-4765-408d-a7d5-3aa102c004c4",
  "project_id": "cad33e49-799e-4bcf-9bbe-839301b95551",
  "status": "queued",
  "output_path": "data\\renders\\cad33e49-799e-4bcf-9bbe-839301b95551.mp4",
  "output_format": "mp4",
  "quality_preset": "standard",
  "progress": 0.0,
  "error_message": null,
  "retry_count": 0,
  "created_at": "2026-04-24T07:25:11.556369Z",
  "updated_at": "2026-04-24T07:25:11.556369Z",
  "completed_at": null
}
```

**Failure modes:**

| HTTP | `detail.code` | Meaning |
|------|---------------|---------|
| 400 | `INVALID_FORMAT` | `output_format` not in `[mp4, webm, mov, mkv]`. |
| 400 | `INVALID_PRESET` | `quality_preset` not in `[draft, standard, high]`. |
| 422 | `INCOMPATIBLE_FORMAT_ENCODER` | Explicit `encoder` cannot produce the requested `output_format`. |
| 422 | `PREFLIGHT_FAILED` | Rust core rejected settings / render plan. |
| 503 | `RENDER_UNAVAILABLE` | Service shutting down or FFmpeg missing from `PATH`. |

The available encoders and format/encoder compatibility matrix are
discoverable at `GET /api/v1/render/formats` and `GET /api/v1/render/encoders`.

### 4.2 Queue status

```bash
curl -s http://localhost:8765/api/v1/render/queue
```

```json
{
  "active_count": 0,
  "pending_count": 1,
  "max_concurrent": 4,
  "max_queue_depth": 50,
  "disk_available_bytes": 386599796736,
  "disk_total_bytes": 1022000173056,
  "completed_today": 0,
  "failed_today": 0
}
```

`pending_count` → increases on submit, drops once a job enters `running`.
`max_concurrent` / `max_queue_depth` are configurable via
`STOAT_RENDER_MAX_CONCURRENT` / `STOAT_RENDER_MAX_QUEUE_DEPTH`.

### 4.3 Status

```bash
curl -s http://localhost:8765/api/v1/render/11b21570-4765-408d-a7d5-3aa102c004c4
```

During an active render, the response shows `status: "running"`,
`progress` monotonically increasing from `0.0` → `1.0`, and
`updated_at` advancing. On completion `status: "completed"` and
`completed_at` is set. Listen on `/ws` for live `render.progress` events
(throttled server-side) instead of polling.

### 4.4 Cancel

```bash
curl -s -X POST http://localhost:8765/api/v1/render/11b21570-4765-408d-a7d5-3aa102c004c4/cancel
```

```json
{
  "id": "11b21570-4765-408d-a7d5-3aa102c004c4",
  "project_id": "cad33e49-799e-4bcf-9bbe-839301b95551",
  "status": "cancelled",
  "output_path": "data\\renders\\cad33e49-799e-4bcf-9bbe-839301b95551.mp4",
  "output_format": "mp4",
  "quality_preset": "standard",
  "progress": 0.0,
  "error_message": null,
  "retry_count": 0,
  "created_at": "2026-04-24T07:25:11.556369Z",
  "updated_at": "2026-04-24T07:29:16.406143Z",
  "completed_at": "2026-04-24T07:29:16.406143Z"
}
```

Cancel rejects with 409 `NOT_CANCELLABLE` once the job is in a terminal
state (`completed`, `failed`, `cancelled`). A failed transient job can be
retried via `POST /api/v1/render/{job_id}/retry` (409 `NOT_RETRYABLE`
when the status is not `failed`, 409 `PERMANENT_FAILURE` when
`retry_count` exceeds `STOAT_RENDER_RETRY_COUNT`).

---

## Workflow 5: Batch render

Submit many render jobs in one request and track aggregated progress.

**Endpoint chain**

1. `POST /api/v1/render/batch` — submit a list of render jobs.
2. `GET /api/v1/render/batch/{batch_id}` — aggregated status and per-job detail.

### 5.1 Submit the batch

```bash
curl -s -X POST http://localhost:8765/api/v1/render/batch \
  -H "Content-Type: application/json" \
  -d '{
        "jobs": [
          {"project_id": "cad33e49-799e-4bcf-9bbe-839301b95551", "output_path": "data/renders/batch_output_1.mp4", "quality": "draft"},
          {"project_id": "cad33e49-799e-4bcf-9bbe-839301b95551", "output_path": "data/renders/batch_output_2.mp4", "quality": "standard"}
        ]
      }'
```

**Response — 202 Accepted:**

```json
{"batch_id": "341eec44-4663-44fb-a490-3b57a2aec78a", "jobs_queued": 2, "status": "accepted"}
```

`batch_max_jobs` (default 20) caps the list size; over-cap requests get
422 `BATCH_JOB_LIMIT_EXCEEDED`. Concurrency inside the batch is bounded
by `STOAT_BATCH_PARALLEL_LIMIT` (default 4).

### 5.2 Poll aggregated progress

```bash
curl -s http://localhost:8765/api/v1/render/batch/341eec44-4663-44fb-a490-3b57a2aec78a
```

```json
{
  "batch_id": "341eec44-4663-44fb-a490-3b57a2aec78a",
  "overall_progress": 1.0,
  "completed_jobs": 2,
  "failed_jobs": 0,
  "total_jobs": 2,
  "jobs": [
    {
      "job_id": "ac7c7dc3-84bd-4710-855e-c18dd0280258",
      "project_id": "cad33e49-799e-4bcf-9bbe-839301b95551",
      "status": "completed",
      "progress": 1.0,
      "error": null
    },
    {
      "job_id": "0201056e-acf3-459f-975c-3d86b2366771",
      "project_id": "cad33e49-799e-4bcf-9bbe-839301b95551",
      "status": "completed",
      "progress": 1.0,
      "error": null
    }
  ]
}
```

`overall_progress` is computed by the Rust core via `calculate_batch_progress`
— it averages individual job progress when jobs are in-flight and becomes
`1.0` only after every job reaches a terminal state. Per-job `status`
values are `pending | running | completed | failed`.

> **Operational note.** Batch jobs run through a handler hook on
> `app.state.batch_render_handler`. When the hook is unset (the default
> for a bare API process) jobs transition `pending → running → completed`
> without actually invoking FFmpeg. Wiring a real handler is the
> deployment's responsibility — see the runbook.

An unknown `batch_id` returns 404 `NOT_FOUND`.

---

## System state snapshot

For dashboards or agent orientation, `GET /api/v1/system/state` returns a
single consistent view of jobs and connections — the same shape the
WebSocket stream uses for its initial snapshot.

```bash
curl -s http://localhost:8765/api/v1/system/state
```

```json
{
  "timestamp": "2026-04-24T07:29:05.210818Z",
  "active_jobs": [
    {
      "job_id": "981c5389-01ba-4f35-a078-72c9a999a756",
      "job_type": "scan",
      "status": "complete",
      "progress": 1.0,
      "submitted_at": "2026-04-24T07:23:48.200424Z"
    }
  ],
  "active_connections": 0,
  "uptime_seconds": 348.27
}
```

WebSocket subscribers bootstrap off this snapshot and then apply incremental
events. Reconnecting clients replay missed events by passing the last
`event_id` via `Last-Event-ID` (see the WebSocket replay pattern in
`docs/framework-context/FRAMEWORK_CONTEXT.md`).

---

## Error handling quick reference

| Status | Shape | Typical trigger |
|--------|-------|-----------------|
| 400 | `{"detail": {"code": "...", "message": "..."}}` | Malformed body, invalid enum value, path is not a directory. |
| 403 | `{"detail": {"code": "PATH_NOT_ALLOWED", ...}}` | Scan path outside `STOAT_ALLOWED_SCAN_ROOTS`. |
| 404 | `{"detail": {"code": "NOT_FOUND", ...}}` | Unknown project / clip / job. `EFFECT_NOT_FOUND` for unknown effect types. |
| 408 | `{"detail": {"code": "JOB_WAIT_TIMEOUT", ...}}` | `/jobs/{id}/wait` deadline passed. Resume by calling again. |
| 409 | `{"detail": {"code": "...", ...}}` | State-machine violation — `NOT_CANCELLABLE`, `NOT_RETRYABLE`, `PERMANENT_FAILURE`, `ALREADY_TERMINAL`, `REFRESH_IN_PROGRESS`. |
| 422 | `{"detail": [ ... ]}` (Pydantic) or `{"detail": {"code": "...", ...}}` | Request validation failure or business-rule rejection (`INCOMPATIBLE_FORMAT_ENCODER`, `PREFLIGHT_FAILED`, `BATCH_JOB_LIMIT_EXCEEDED`). |
| 503 | `{"detail": {"code": "...", ...}}` | Subsystem unavailable — `RENDER_UNAVAILABLE`, `FFMPEG_UNAVAILABLE`, `SERVICE_UNAVAILABLE`. |

Sample 404 and 400 responses captured from the live run:

```bash
curl -s -w "\n%{http_code}\n" http://localhost:8765/api/v1/projects/nonexistent
# {"detail":{"code":"NOT_FOUND","message":"Project nonexistent not found"}}
# 404

curl -s -w "\n%{http_code}\n" -X POST http://localhost:8765/api/v1/render \
  -H "Content-Type: application/json" \
  -d '{"project_id":"nonexistent","output_format":"xyz","quality_preset":"standard","render_plan":"{}"}'
# {"detail":{"code":"INVALID_FORMAT","message":"Invalid output format: xyz. Valid: ['mp4', 'webm', 'mov', 'mkv']"}}
# 400
```

---

## Keeping this document honest

Every workflow above was executed against a locally-built server on
2026-04-24 following the procedure in
[`docs/design/VALIDATION_FRAMEWORK.md`](../design/VALIDATION_FRAMEWORK.md).
When an endpoint signature, response shape, or error code changes,
re-run the corresponding curl chain and refresh the affected snippets
in the same PR. The OpenAPI schema at `gui/openapi.json` (and the live
`/docs` UI) remain the single source of truth for the full catalogue;
this document trades exhaustiveness for runnable narrative examples.
