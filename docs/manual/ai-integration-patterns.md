# AI Integration Patterns

Five canonical patterns for AI agents integrating with the stoat-and-ferret
API. Each pattern lists prerequisites, the interaction shape, a validated
`curl` example, and error-handling guidance.

All examples assume the API is running at `http://localhost:8765` and were
validated against `main` after BL-270 (`/api/v1/effects` enrichment) and
BL-271 (`/api/v1/schema/{resource}`) landed.

For the broader orientation and Python/`httpx` examples, see
[08_ai-integration.md](08_ai-integration.md). This guide focuses on the
canonical request shapes a language model needs to bootstrap itself from
live endpoints alone.

---

## Pattern 1: Discovery

**Goal**: Discover available effects and their parameter constraints from a
single endpoint, without offline documentation.

**Prerequisites**: API running at `http://localhost:8765`.

**Interaction**:
1. Agent calls `GET /api/v1/effects` once per session.
2. Response contains each effect's `effect_type`, `name`, `description`,
   `parameter_schema` (raw JSON Schema), `parameters` (structured list),
   `ai_summary`, `example_prompt`, and `filter_preview`.
3. Agent parses the `parameters` list to learn `param_type`, bounds
   (`min_value` / `max_value`), `enum_values`, and per-parameter
   `ai_hint`.

**Curl Example**:

```bash
curl -s http://localhost:8765/api/v1/effects \
  | jq '.effects[] | {effect_type, ai_summary, example_prompt}'
```

**Expected Response** (abbreviated, one effect shown):

```json
{
  "effect_type": "text_overlay",
  "ai_summary": "Burn captions, titles, or watermark text onto a video clip.",
  "example_prompt": "Add the caption \"Breaking News\" in the bottom center of the clip."
}
```

Drill into a single effect's structured parameter list:

```bash
curl -s http://localhost:8765/api/v1/effects \
  | jq '.effects[] | select(.effect_type == "text_overlay") | .parameters[] | select(.name == "fontsize")'
```

```json
{
  "name": "fontsize",
  "param_type": "int",
  "default_value": 48,
  "min_value": 8.0,
  "max_value": 256.0,
  "enum_values": null,
  "description": "Font size in pixels",
  "ai_hint": "Font size in pixels, typical range 12-72"
}
```

**Error Handling**:
- If `/api/v1/effects` returns `500`, the registry failed to initialize —
  check server logs.
- If an effect's `parameters` list is empty, the effect has no configurable
  parameters; `ai_hints` may still exist for positional or implicit
  settings.

---

## Pattern 2: Schema Learning

**Goal**: Learn the response shape of a domain entity without parsing the
full OpenAPI document.

**Prerequisites**: API running.

**Interaction**:
1. Agent calls `GET /api/v1/schema/{resource}` for one of: `project`,
   `clip`, `timeline`, `render_job`, `effect`, `video`.
2. Response is the Pydantic-generated JSON Schema (`model_json_schema()`)
   for the response model. Fields include `properties`, `required`,
   `title`, and `description`.
3. Agent uses the schema to plan which fields to send or parse. Request
   bodies are not exposed here — agents fall back to `/openapi.json` for
   request schemas.

**Curl Example**:

```bash
curl -s http://localhost:8765/api/v1/schema/project | jq '.properties | keys'
```

**Expected Response**:

```json
["created_at", "id", "name", "output_fps", "output_height", "output_width", "updated_at"]
```

Full schema output (abbreviated):

```bash
curl -s http://localhost:8765/api/v1/schema/clip | jq '.required'
```

```json
["id", "project_id", "source_video_id", "in_point", "out_point", "timeline_position", "created_at", "updated_at"]
```

**Error Handling**:
- Unknown resource names return `404` with
  `{"detail": "Unknown resource: <name>"}`. Valid names are listed above.
- The endpoint returns response-model schemas only. For create-request
  bodies (e.g. `ProjectCreate`, `ClipCreate`), use
  `/openapi.json` → `components.schemas.<ModelName>`.

---

## Pattern 3: Execute

**Goal**: Construct and submit effect applications and render jobs using
the schemas learned in Patterns 1 and 2.

**Prerequisites**: Patterns 1 and 2 complete. Agent has a video ID (from
`GET /api/v1/videos`) or is willing to create a project first.

**Interaction**:
1. Create a project: `POST /api/v1/projects`.
2. Add a clip to the project: `POST /api/v1/projects/{project_id}/clips`.
3. Apply an effect to the clip:
   `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects`.
4. Submit a render: `POST /api/v1/render`.
5. Poll render status: `GET /api/v1/render/{job_id}` until
   `status` is `completed`, `failed`, or `cancelled`.

**Curl Example**:

```bash
# 1. Create project (201 Created)
PROJECT_ID=$(curl -s -X POST http://localhost:8765/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"AgentDemo"}' | jq -r '.id')

# 2. List available videos and pick the first one
VIDEO_ID=$(curl -s "http://localhost:8765/api/v1/videos?limit=1" | jq -r '.videos[0].id')

# 3. Add a clip spanning frames 0..150 of that video
CLIP_ID=$(curl -s -X POST "http://localhost:8765/api/v1/projects/$PROJECT_ID/clips" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_video_id\": \"$VIDEO_ID\",
    \"in_point\": 0,
    \"out_point\": 150,
    \"timeline_position\": 0
  }" | jq -r '.id')

# 4. Apply a text_overlay effect to the clip
curl -s -X POST "http://localhost:8765/api/v1/projects/$PROJECT_ID/clips/$CLIP_ID/effects" \
  -H "Content-Type: application/json" \
  -d '{
    "effect_type": "text_overlay",
    "parameters": {"text": "Hello AI", "fontsize": 48}
  }' | jq '{effect_type, filter_string}'

# 5. Submit a render job (201 Created)
JOB_ID=$(curl -s -X POST http://localhost:8765/api/v1/render \
  -H "Content-Type: application/json" \
  -d "{\"project_id\": \"$PROJECT_ID\", \"output_format\": \"mp4\", \"quality_preset\": \"draft\"}" \
  | jq -r '.id')

# 6. Poll render status
curl -s "http://localhost:8765/api/v1/render/$JOB_ID" | jq '{id, status, progress}'
```

**Expected Effect Application Response**:

```json
{
  "effect_type": "text_overlay",
  "filter_string": "drawtext=text=Hello AI:fontsize=48:fontcolor=black"
}
```

**Expected Render Job Response**:

```json
{
  "id": "f296e269-9103-4292-ba8a-fa8c48805cc8",
  "status": "queued",
  "progress": 0.0
}
```

**Error Handling**:
- `400 INVALID_FORMAT` / `INVALID_PRESET` from `POST /api/v1/render` —
  the body's `output_format` or `quality_preset` is not in the allowed
  enum. Call `GET /api/v1/render/formats` for the current list.
- `400 EFFECT_NOT_FOUND` from the effect apply endpoint — `effect_type`
  does not match any effect returned by Pattern 1.
- `404 NOT_FOUND` — the project or clip was deleted between creation
  and the follow-up call. Recreate or re-fetch.
- `422 Unprocessable Entity` — the request body failed Pydantic
  validation. Inspect `detail` for the offending field path and
  cross-reference Pattern 2's schema.

---

## Pattern 4: Batch

**Goal**: Submit multiple render jobs in one request and handle partial
progress independently per job.

**Prerequisites**: Pattern 3 working for a single render.

**Interaction**:
1. Agent builds a list of `BatchJobConfig` entries — one per project to
   render. Each entry requires `project_id` and `output_path`; `quality`
   is optional (defaults to `medium`).
2. Agent submits `POST /api/v1/render/batch` with
   `{"jobs": [...]}`. The server queues all jobs and returns a
   `batch_id` plus `jobs_queued` count.
3. Agent polls individual job status via the batch endpoint or polls each
   underlying render job by ID.
4. On partial failure, the agent retries only the failed `project_id`
   entries in a new batch — do not retry the whole batch.

The endpoint does **not** currently support an `X-Idempotency-Key`
header; agents that need idempotency must check existing project state
(e.g. `GET /api/v1/render?project_id=...`) before submitting.

**Curl Example**:

```bash
# Submit two render jobs in one batch
curl -s -X POST http://localhost:8765/api/v1/render/batch \
  -H "Content-Type: application/json" \
  -d '{
    "jobs": [
      {"project_id": "7ebe3714-fcf0-4a65-bdf9-dae837d74662", "output_path": "data/renders/agent1.mp4", "quality": "draft"},
      {"project_id": "e93cd851-0c4f-47c8-9d14-6f8e47dca919", "output_path": "data/renders/agent2.mp4", "quality": "medium"}
    ]
  }' | jq

# Poll batch status
curl -s "http://localhost:8765/api/v1/render/batch/$BATCH_ID" | jq
```

**Expected Submit Response**:

```json
{
  "batch_id": "8c4b5f12-1e39-48a7-9b2a-1c4a2b5f7e80",
  "jobs_queued": 2,
  "status": "accepted"
}
```

Polling `GET /api/v1/render/batch/{batch_id}` returns aggregate progress
plus a per-job breakdown — each job carries its own `job_id`, `status`,
`progress`, and optional `error`:

```json
{
  "batch_id": "8c4b5f12-1e39-48a7-9b2a-1c4a2b5f7e80",
  "overall_progress": 1.0,
  "completed_jobs": 2,
  "failed_jobs": 0,
  "total_jobs": 2,
  "jobs": [
    {"job_id": "...", "project_id": "...", "status": "completed", "progress": 1.0, "error": null},
    {"job_id": "...", "project_id": "...", "status": "completed", "progress": 1.0, "error": null}
  ]
}
```

**Error Handling**:
- `422` — `jobs` list was empty (min-items is 1) or exceeded
  `Settings.batch_max_jobs`. Split oversized batches.
- `400` on submit — one or more `project_id` values are not valid
  UUIDs or refer to deleted projects.
- Partial per-job failure after queueing surfaces on the individual
  `GET /api/v1/render/{job_id}` response as
  `status=failed, error_message=...`. Retry only the failed project IDs.

---

## Pattern 5: Reconnection

**Goal**: Reconnect to the event stream after a network interruption and
resync agent state with minimal REST polling.

**Prerequisites**: Patterns 1–3 working; agent has a WebSocket client.

**Interaction**:
1. Agent connects to `ws://localhost:8765/ws`. The server immediately
   accepts and starts streaming events and periodic `heartbeat`
   messages.
2. Every frame is a JSON object with `type`, `payload`,
   `correlation_id`, and `timestamp` fields. `type` values include
   `heartbeat`, `render_queued`, `render_started`, `render_progress`,
   `render_completed`, `render_failed`, `render_cancelled`,
   `scan_completed`, `project_created`, `timeline_updated`, and others
   (see [08_ai-integration.md](08_ai-integration.md) for the full
   vocabulary).
3. Persist each frame's `event_id` field as you process it. On
   reconnect, send `Last-Event-ID: <last-seen-event-id>` as an HTTP
   header during the WebSocket upgrade handshake — the server replays
   buffered events strictly newer than that id. Replay fires **once** at
   accept time; subsequent frames after reconnect are live broadcasts.
   Heartbeat frames are excluded from replay.
4. The replay buffer has a TTL of `ws_replay_ttl_seconds` (default:
   **300 seconds / 5 minutes**). Events older than the TTL are dropped
   before the `Last-Event-ID` lookup. If the TTL has expired or the
   server restarted, fall back to `GET /api/v1/system/state` to
   reconcile jobs that terminated while disconnected.
5. Heartbeat frames arrive on a fixed interval (see
   `ws_heartbeat_interval` setting). An agent that stops receiving
   heartbeats for significantly longer than that interval should treat
   the connection as dead and reconnect.

**Curl / `wscat` Example** (install `wscat` via `npm install -g wscat`):

```bash
# Initial connect — no replay
wscat -c ws://localhost:8765/ws

# Reconnect with Last-Event-ID to replay missed events
wscat -c ws://localhost:8765/ws -H "Last-Event-ID: event-00042"
```

Observed frames while a render is running:

```json
{"type":"render_queued","payload":{"job_id":"...","project_id":"..."},"correlation_id":null,"timestamp":"2026-04-23T00:57:17.631983Z"}
{"type":"render_started","payload":{"job_id":"..."},"correlation_id":null,"timestamp":"..."}
{"type":"render_progress","payload":{"job_id":"...","progress":0.42},"correlation_id":null,"timestamp":"..."}
{"type":"render_completed","payload":{"job_id":"...","output_path":"..."},"correlation_id":null,"timestamp":"..."}
{"type":"heartbeat","payload":{},"correlation_id":null,"timestamp":"..."}
```

**Error Handling**:
- If the WebSocket closes unexpectedly, reconnect immediately with
  exponential backoff (1s, 2s, 4s, max 30s). Do not tear down agent
  state on the first drop.
- When reconnecting, include `Last-Event-ID: <last-event-id>` to
  receive buffered events missed during the outage (within the 300-second
  TTL window). If the TTL has expired or the server restarted, poll
  `GET /api/v1/render/queue` and `GET /api/v1/render/{job_id}` for
  every job the agent had in flight to reconcile state.
- If no heartbeat arrives for `3 * ws_heartbeat_interval`, close the
  socket and reconnect — the underlying TCP connection is likely
  stale.

---

## Cross-Cutting Guidance

### Retries

- Retry idempotent GETs on `5xx` and network errors with exponential
  backoff (1s, 2s, 4s, max 30s; cap 5 attempts).
- Do **not** blindly retry `POST /api/v1/render` or effect-application
  POSTs on `5xx` without first checking
  `GET /api/v1/render?project_id=...` or the clip's `effects` array —
  the first attempt may have partially succeeded.
- Do not retry `4xx` responses except `429` (rate-limited, if
  introduced) or `409` (conflict) with a small delay.

### Validation Loop

When a `422` is returned, an agent should:
1. Parse `detail` to find the offending field path.
2. Re-fetch the relevant schema via Pattern 2.
3. Coerce or drop the offending field and retry once.
4. If the retry also fails, surface the raw error to the operator —
   the agent is missing context.

### Correlation IDs

For cross-service tracing, send an `X-Correlation-ID` request header on
every HTTP call. The same ID is emitted on WebSocket events triggered
by that request and appears in structured server logs. See
[08_ai-integration.md](08_ai-integration.md) for a worked example.

### Discoverability From Zero

A brand-new agent only needs three endpoints to bootstrap:

1. `GET /openapi.json` — full API surface area.
2. `GET /api/v1/effects` — enriched effect metadata with
   `parameters`, `ai_summary`, `example_prompt`.
3. `GET /api/v1/schema/{resource}` — per-resource response schemas.

No other documentation is required to construct valid requests for the
REST endpoints.

---

## References

- [08_ai-integration.md](08_ai-integration.md) — broader AI integration
  overview, Python workflow examples, and natural-language mapping
  table.
- [03_api-reference.md](03_api-reference.md) — complete endpoint
  reference.
- [04_effects-guide.md](04_effects-guide.md) — per-effect parameter
  reference.
- `comms/outbox/versions/design/v039/` — design rationale, risk
  analysis, and test strategy for this guide.
