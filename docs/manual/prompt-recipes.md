# Prompt Recipes for AI Agents

Copy-paste recipes for orchestrating stoat-and-ferret over HTTP/WebSocket. Each recipe pairs an LLM-facing **prompt preamble** with the exact API sequence, request bodies, and response shape an agent should expect. Recipes assume the server is reachable at `http://localhost:8765`; substitute `STOAT_API_HOST`/`STOAT_API_PORT` for non-default deployments.

For surrounding context see `operator-guide.md` (canonical sequences), `api-usage-examples.md` (error semantics), and `ws-event-vocabulary.md` (event payloads). Runnable companions live under `scripts/examples/`.

## Recipe Index

1. [Scan → Render Cycle](#1-scan--render-cycle)
2. [Apply Effect to a Specific Clip](#2-apply-effect-to-a-specific-clip)
3. [Seed a Project Fixture (Testing Mode)](#3-seed-a-project-fixture-testing-mode)
4. [Long-Poll for Async Job Completion](#4-long-poll-for-async-job-completion)
5. [WebSocket Event Monitoring with Reconnect](#5-websocket-event-monitoring-with-reconnect)
6. [Batch Render Workflow](#6-batch-render-workflow)

Recipes assume happy-path usage. The four error codes most agents need are `JOB_WAIT_TIMEOUT` (408), `INVALID_PRESET` / `INVALID_FORMAT` (400), `TESTING_MODE_DISABLED` (403), and `NOT_FOUND` (404); see `api-usage-examples.md` for full payloads.

---

## 1. Scan → Render Cycle

End-to-end happy path: scan a directory, build a one-clip project, render to disk.

### Prompt Preamble

> You are operating the stoat-and-ferret HTTP API at `http://localhost:8765`. The user wants to render the first video found under `<scan_path>` to `<output_format>` (default `mp4`) at `quality_preset` (one of `draft`, `standard`, `high`). Submit the scan, wait for it to terminate, pick the first returned `video_id`, create a project, attach the clip starting at frame 0 for its full source duration, kick off the render, and report `output_path` once the render job reaches `"completed"`.

### API Sequence

| # | Request | Status | Purpose |
|---|---------|--------|---------|
| 1 | `POST /api/v1/videos/scan` | 202 | Enqueue scan job |
| 2 | `GET /api/v1/jobs/{job_id}/wait?timeout=30` | 200 | Block until scan terminal |
| 3 | `GET /api/v1/videos?limit=1` | 200 | Pick the first `video_id` |
| 4 | `POST /api/v1/projects` | 201 | Create project shell |
| 5 | `POST /api/v1/projects/{project_id}/clips` | 201 | Attach the clip (in/out points are integer frame counts) |
| 6 | `POST /api/v1/render` | 201 | Start render job |
| 7 | `GET /api/v1/render/{job_id}` (repeat every 1–2 s until terminal) | 200 | Poll until `status ∈ {completed, failed, cancelled}` |

### Sample Request Bodies

```jsonc
// 1. Scan request
{ "path": "/abs/path/to/videos", "recursive": true }

// 4. Project create
{ "name": "demo", "output_width": 1920, "output_height": 1080, "output_fps": 30 }

// 5. Clip create — in_point/out_point/timeline_position are frame counts (integers)
{ "source_video_id": "<video_id>", "in_point": 0, "out_point": 300, "timeline_position": 0 }

// 6. Render create — quality_preset must be one of draft|standard|high
{ "project_id": "<project_id>", "output_format": "mp4", "quality_preset": "standard" }
```

### Sample Response Shapes

```jsonc
// Step 1 → JobSubmitResponse (202)
{ "job_id": "job_abc123" }

// Step 2 → JobStatusResponse (200, terminal)
{ "job_id": "job_abc123", "status": "complete", "progress": 1.0,
  "result": { "scanned": 5, "new": 5, "updated": 0, "errors": [] }, "error": null }

// Step 3 → VideoListResponse
{ "videos": [{ "id": "vid_…", "filename": "intro.mp4", "duration_frames": 300, … }],
  "total": 1, "limit": 1, "offset": 0 }

// Step 6 → RenderJobResponse (id is the job_id for polling GET /api/v1/render/{id})
{ "id": "job_xyz789", "project_id": "<project_id>", "status": "queued",
  "output_path": "/abs/render/dir/<project_id>.mp4", "output_format": "mp4",
  "quality_preset": "standard", "progress": 0.0, "retry_count": 0, … }

// Step 7 → RenderJobResponse (200, terminal)
{ "job_id": "job_xyz789", "status": "completed", "progress": 1.0,
  "result": { "output_path": "/abs/render/dir/<project_id>.mp4", … }, "error": null }
```

### Error Notes

- The 202 from step 1 only confirms enqueue; check `result.errors` on the terminal status — a missing path produces a `complete` job with non-empty `errors`.
- Step 6 returns `400 INVALID_PRESET` if `quality_preset` is not `draft|standard|high`.
- If the wait endpoint returns `408 JOB_WAIT_TIMEOUT`, the job is still running; re-call with the same `job_id`.

---

## 2. Apply Effect to a Specific Clip

Find an existing project, locate one of its clips, and append an effect by type.

### Prompt Preamble

> The user wants to apply a `<effect_type>` (e.g. `volume`) effect with parameters `<parameters>` to the clip at `timeline_position` `<position>` inside project `<project_id>`. Look up the project's clips, match the position, then attach the effect via the clips/effects endpoint and confirm the returned `filter_string`.

### API Sequence

| # | Request | Status | Purpose |
|---|---------|--------|---------|
| 1 | `GET /api/v1/projects/{project_id}` | 200 | Confirm project exists |
| 2 | `GET /api/v1/projects/{project_id}/clips` | 200 | Find target `clip_id` by `timeline_position` |
| 3 | `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` | 201 | Apply effect |

### Sample Request Body

```jsonc
// 3. Effect apply
{
  "effect_type": "volume",
  "parameters": { "volume": 0.5 }
}
```

### Sample Response

```jsonc
// 3. EffectApplyResponse
{
  "effect_type": "volume",
  "parameters": { "volume": 0.5 },
  "filter_string": "volume=volume=0.5"
}
```

### Error Notes

- Effect type discovery: `GET /api/v1/effects` returns the supported list with parameter schemas.
- `GET /api/v1/effects/{effect_type}/preview` (POST in some builds) lets you validate parameters before persisting.
- Step 3 returns `422` for parameter schema violations — payload includes the offending field path.

---

## 3. Seed a Project Fixture (Testing Mode)

Use the testing-mode seed endpoints to skip the full scan→project→clip path during smoke runs. Requires `STOAT_TESTING_MODE=true` on the server process; otherwise both calls return `403 TESTING_MODE_DISABLED`.

### Prompt Preamble

> The server is running with `STOAT_TESTING_MODE=true`. Seed a project fixture named `<name>` (server prepends `seeded_`) with output dimensions `<width>x<height>@<fps>` and remember the `fixture_id` so you can tear it down at the end.

### API Sequence

| # | Request | Status | Purpose |
|---|---------|--------|---------|
| 1 | `POST /api/v1/testing/seed` | 201 | Create fixture |
| 2 | `DELETE /api/v1/testing/seed/{fixture_id}?fixture_type=project` | 204 | Tear it down |

### Sample Request

```jsonc
// 1. Seed project — do NOT pre-prefix `seeded_`; server adds it (INV-SEED-2)
{
  "fixture_type": "project",
  "name": "smoke-demo",
  "data": { "output_width": 1280, "output_height": 720, "output_fps": 30 }
}
```

### Sample Response

```jsonc
// 1. SeedResponse (201)
{
  "fixture_id": "proj_01HXZ2T9CK3Q4R5S6T7U8V9W0X",
  "fixture_type": "project",
  "name": "seeded_smoke-demo"
}
```

### Error Notes

- `403 TESTING_MODE_DISABLED` — start the server with `STOAT_TESTING_MODE=true`.
- `422` — only `fixture_type: "project"` is supported in this release; other values are rejected.
- `404` on delete — fixture id was never created or already deleted.

---

## 4. Long-Poll for Async Job Completion

Use `/api/v1/jobs/{job_id}/wait` instead of a `time.sleep` polling loop for **scan and other background jobs**. Render jobs use a different namespace — poll `GET /api/v1/render/{job_id}` instead (see [Recipe 1: Scan → Render Cycle](#1-scan--render-cycle)).

### Prompt Preamble

> You have a `job_id` from a prior scan or other background job submission. Block until the job reaches a terminal state (`complete`, `failed`, `timeout`, `cancelled`) using `GET /api/v1/jobs/{job_id}/wait?timeout=N`. If the call returns `408 JOB_WAIT_TIMEOUT`, the job is still running on the server — re-issue the call with the same `job_id`. Treat any other non-200 as a terminal failure for the workflow. **Render jobs use `/api/v1/render/{job_id}` polling** (different namespace — see Recipe 1).

### API Sequence

| # | Request | Status | Behaviour |
|---|---------|--------|-----------|
| 1 | `GET /api/v1/jobs/{job_id}/wait?timeout=30` | 200 | Returns `JobStatusResponse` once terminal |
| — | (same) | 408 | `JOB_WAIT_TIMEOUT`; re-call with same `job_id` |
| — | (same) | 404 | `job_id` unknown; treat as terminal failure |

### Parameter Constraints

- `timeout` is clamped to `[1, 3600]` (seconds). Server returns 422 for values outside the range.
- Server restart while a waiter is blocked surfaces as a 408, not a replay — re-issue.

### Sample Responses

```jsonc
// Terminal success
{ "job_id": "job_xyz", "status": "complete", "progress": 1.0,
  "result": { "output_path": "...", "scanned": 5 }, "error": null }

// Terminal failure
{ "job_id": "job_xyz", "status": "failed", "progress": 0.42,
  "result": null, "error": "ffmpeg: exit code 1" }

// 408 timeout body
{ "detail": { "code": "JOB_WAIT_TIMEOUT",
              "message": "Job did not reach terminal state in 30s" } }
```

The runnable companion is `scripts/examples/wait-for-render.py`.

---

## 5. WebSocket Event Monitoring with Reconnect

Stream events via the global WebSocket `/ws` and reconnect using `Last-Event-ID` to skip already-seen frames. The server maintains a single global replay buffer (`ws_replay_buffer_size`) with `ws_replay_ttl_seconds` TTL; heartbeats are excluded from replay.

### Prompt Preamble

> Connect a long-lived WebSocket to `ws://localhost:8765/ws`. Each frame is JSON with `{event_id, type, payload, correlation_id, timestamp}`. Persist the latest `event_id` you successfully processed. On reconnect, send the WebSocket handshake with header `Last-Event-ID: <event_id>` so the server replays buffered frames strictly newer than that id. If the id is missing from the buffer (TTL expired or restart), expect every still-buffered frame instead. Ignore `type: "heartbeat"`; also reconcile against `GET /api/v1/system/state` after a long disconnection.

### API Sequence

1. Open WebSocket: `ws://localhost:8765/ws`
2. Read frames in a loop; persist `event_id` from each non-heartbeat frame
3. On disconnect, reopen the socket with HTTP header `Last-Event-ID: <last_seen>`
4. After a long outage, also poll `GET /api/v1/system/state` to enumerate `active_jobs` that may have terminated outside the replay window

### Sample Frames

```jsonc
// scan_started
{ "event_id": "event-00001", "type": "scan_started",
  "payload": { "job_id": "job_abc", "path": "/videos" },
  "correlation_id": "corr_…", "timestamp": "2026-04-25T12:00:00.123Z" }

// render_progress (one of many)
{ "event_id": "event-00007", "type": "render_progress",
  "payload": { "job_id": "job_xyz", "progress": 0.42 },
  "correlation_id": "corr_…", "timestamp": "2026-04-25T12:00:05.456Z" }

// terminal
{ "event_id": "event-00009", "type": "render_completed",
  "payload": { "job_id": "job_xyz", "output_path": "..." },
  "correlation_id": "corr_…", "timestamp": "2026-04-25T12:00:09.789Z" }

// ignore
{ "event_id": "event-00010", "type": "heartbeat", "payload": {},
  "correlation_id": null, "timestamp": "2026-04-25T12:00:15.000Z" }
```

The runnable companion is `scripts/examples/dump-ws-events.py`.

### Error Notes

- WebSocket close frames may surface as `1001`/`1011`; treat as transient and retry with `Last-Event-ID`.
- `event_id` counter is **per `job_id` scope**, plus a global fallback for events without a job — do not assume a strict global ordering across scopes.

---

## 6. Batch Render Workflow

Submit multiple render jobs in one call, then poll the batch status until all jobs are terminal.

### Prompt Preamble

> The user has a list of `(project_id, output_path)` pairs and wants them rendered concurrently. Submit the batch in one POST, persist the returned `batch_id`, then poll the batch status endpoint every few seconds (or subscribe to `/ws` for `render_progress` / `render_completed` / `render_failed` events). Report the per-job results once every entry's `status` is terminal.

### API Sequence

| # | Request | Status | Purpose |
|---|---------|--------|---------|
| 1 | `POST /api/v1/render/batch` | 201 | Submit batch |
| 2 | `GET /api/v1/render/batch/{batch_id}` | 200 | Poll per-job status |
| 2b | (alternative) `WS /ws` | — | Subscribe to events; filter by `payload.job_id` ∈ batch |

### Sample Request Body

```jsonc
// 1. Batch submit
{
  "jobs": [
    { "project_id": "<proj_a>", "output_path": "/abs/out/a.mp4", "quality": "standard" },
    { "project_id": "<proj_b>", "output_path": "/abs/out/b.mp4", "quality": "draft" }
  ]
}
```

### Sample Response

```jsonc
// 1. BatchResponse (201)
{ "batch_id": "batch_01HXZ…", "jobs_queued": 2, "status": "accepted" }

// 2. BatchJobStatusResponse[] from GET /api/v1/render/batch/{batch_id}
[
  { "job_id": "job_a1", "project_id": "<proj_a>", "status": "completed", "progress": 1.0, "error": null },
  { "job_id": "job_b1", "project_id": "<proj_b>", "status": "running", "progress": 0.42, "error": null }
]
```

### Error Notes

- Maximum jobs per batch is enforced by `Settings.batch_max_jobs`; oversize batches return `422`.
- The batch endpoint accepts `quality` keys `draft|standard|high` (alias `medium` is rejected, matching the single-render endpoint).
- An individual job's failure does not abort siblings; check each entry's `status` and `error`.

---

## See Also

- [`operator-guide.md`](operator-guide.md) — compact canonical sequence reference
- [`api-usage-examples.md`](api-usage-examples.md) — full error code catalogue and validated request/response flows
- [`ws-event-vocabulary.md`](ws-event-vocabulary.md) — event type catalogue with payload schemas
- [`scripts/examples/wait-for-render.py`](../../scripts/examples/wait-for-render.py) — runnable long-poll wrapper (stdlib-only)
- [`scripts/examples/dump-ws-events.py`](../../scripts/examples/dump-ws-events.py) — runnable WebSocket dumper (`websockets>=12.0`)
