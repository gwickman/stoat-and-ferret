# Phase 6: API Endpoints

## New Endpoints

### GET /api/v1/version

Returns build and version metadata for deployment verification.

**Response 200:**
```json
{
  "app_version": "0.6.0",
  "core_version": "0.6.0",
  "build_timestamp": "2026-04-20T10:00:00Z",
  "git_sha": "abc1234",
  "python_version": "3.12.3",
  "database_version": 15
}
```

**Error codes:** None — always returns 200.

### GET /api/v1/system/state

Denormalised snapshot of system state for external agents. Returns projects, active jobs, preview sessions, and queue status in a single request.

**Response 200:**
```json
{
  "timestamp": "2026-04-20T10:05:00Z",
  "projects": [{"id": "p1", "name": "Demo", "clip_count": 3, "track_count": 2, "last_modified": "..."}],
  "active_jobs": [{"id": "j1", "job_type": "render", "status": "running", "progress": 0.45, "created_at": "..."}],
  "preview_sessions": [],
  "queue_status": {"pending": 0, "running": 1, "completed_last_hour": 5},
  "health": {"live": true, "ready": true, "database": "ok", "rust_core": "ok"}
}
```

**Error codes:** 503 if database unreachable.

### POST /api/v1/testing/seed

Creates test fixture data. **Only available when `STOAT_TESTING_MODE=true`**. Returns 404 when guard is off.

**Request:**
```json
{
  "fixture_name": "render-ready",
  "project_count": 1,
  "videos_per_project": 2,
  "include_render_jobs": true,
  "include_proxy_files": false
}
```

**Response 201:**
```json
{
  "seeded": true,
  "project_ids": ["p-seed-001"],
  "video_ids": ["v-seed-001", "v-seed-002"],
  "message": "Seeded 1 project with 2 videos and 1 render job"
}
```

**Error codes:** 404 (testing mode disabled), 422 (invalid fixture_name).

### DELETE /api/v1/testing/seed

Tears down all seeded data. Same config guard as POST.

**Response 200:** `{"cleared": true, "message": "All seeded data removed"}`

### GET /api/v1/effects (enhanced)

Existing endpoint — enhanced with AI discovery fields.

**New response fields per effect:**
```json
{
  "name": "drawtext",
  "parameters": [
    {
      "name": "font_size",
      "param_type": "int",
      "default_value": "24",
      "min_value": 8,
      "max_value": 256,
      "description": "Font size in pixels",
      "ai_hint": "Use 24-48 for subtitles, 64-128 for titles. Scale with output resolution."
    }
  ],
  "ai_summary": "Renders text overlay on video. Common uses: subtitles, watermarks, timestamps.",
  "example_prompt": "Add a white subtitle 'Hello World' at the bottom center with font size 36"
}
```

### GET /api/v1/schema/{resource}

Returns JSON Schema for a named API resource. Enables AI agents to learn request/response shapes programmatically.

**Path params:** `resource` — one of: `project`, `clip`, `timeline`, `render_job`, `effect`, `video`

**Response 200:** Standard JSON Schema object.

**Error codes:** 404 (unknown resource).

### GET /api/v1/flags

Returns current feature flag state. Read-only.

**Response 200:**
```json
{
  "testing_mode": false,
  "seed_endpoint": false,
  "synthetic_monitoring": true,
  "batch_rendering": true
}
```

## Long-Poll Pattern

New query parameter `?wait=true&timeout=30` on job status endpoints:

- `GET /api/v1/jobs/{id}?wait=true&timeout=30`
- `GET /api/v1/render/jobs/{id}/status?wait=true&timeout=30`
- `GET /api/v1/render/batch/{id}?wait=true&timeout=30`

**Behaviour:** If job is in a terminal state, returns immediately. Otherwise, holds the connection until the job reaches a terminal state or timeout expires. Returns current status on timeout (not an error).

**Implementation:** `asyncio.Event` per job, set by job queue on state transition. Long-poll handler awaits the event with `asyncio.wait_for()`.

## WebSocket Enhancements

### Reconnection with Replay

**New query parameter:** `ws://host/ws?last_event_id={id}`

When a client connects with `last_event_id`, the server replays all buffered events after that ID. Events are stored in a bounded ring buffer (1000 events, 5-minute TTL).

**New event fields (all events):**
```json
{
  "event_id": "evt-00042",
  "timestamp": "2026-04-20T10:05:00.123Z",
  "type": "render.progress",
  "data": { ... }
}
```

### Event Sequence Guarantees

- Events within a single job are delivered in order (monotonic event_id per job).
- Cross-job ordering is best-effort (no global total order guarantee).
- Heartbeat events are excluded from replay buffer.

## Modified Endpoints

| Endpoint | Change | Milestone |
|----------|--------|-----------|
| `GET /api/v1/effects` | Add `ai_hint`, `ai_summary`, `example_prompt` fields | M6.3 |
| `GET /api/v1/health/ready` | Add `database_version` and `core_version` to response | M6.2 |
| `POST /api/v1/render/batch` | Validate format-encoder compatibility at submission (BL-258) | v037 |
| `WS /ws` | Add `event_id`, `timestamp`, replay via `last_event_id` param | M6.7 |
| Job status endpoints | Add `?wait=true&timeout=N` long-poll support | M6.7 |
