# WebSocket Event Vocabulary

Authoritative reference for every event emitted on `/ws`. Use this document to build deterministic event handlers — agents that ignore unknown event types or misparse payloads will diverge from server state.

Source of truth: `src/stoat_ferret/api/websocket/events.py` (the `EventType` enum) plus the broadcast call sites enumerated below. This vocabulary covers v042 emissions and the v040 envelope additions (`event_id`, `timestamp` — BL-273).

For surrounding context see [`operator-guide.md`](operator-guide.md) (state machines), [`prompt-recipes.md`](prompt-recipes.md) §5 (long-poll companion + Last-Event-ID reconnect example), and [`api-usage-examples.md`](api-usage-examples.md) (error semantics).

---

## Frame Envelope

Every frame emitted on `/ws` (including replays) is a flat JSON object with the same five top-level fields:

```jsonc
{
  "type":           "scan_started",                 // EventType string
  "payload":        { /* event-specific fields */ },
  "correlation_id": "9bab51d4-…" /* or */ null,     // request-scoped trace id
  "timestamp":      "2026-04-26T17:24:55.055181+00:00", // ISO 8601, UTC
  "event_id":       "event-00000"                   // monotonic, globally unique (since BL-356)
}
```

| Field | Type | Notes |
|-------|------|-------|
| `type` | string | One of the 24 `EventType` values listed below. Stable wire format. |
| `payload` | object | Event-specific. Empty `{}` for `heartbeat`. Always present. |
| `correlation_id` | string \| null | The HTTP request's correlation id when the event is broadcast inside a request handler; `null` for events emitted outside a request scope (heartbeats, async-job progress, recovery). |
| `timestamp` | string | ISO 8601 with timezone (always UTC). Use for ordering within a scope and for replay TTL filtering. |
| `event_id` | string | `event-NNNNN` (zero-padded). Persist this to drive `Last-Event-ID` reconnect. |

### `event_id` Global Counter (BL-356)

All events — including render lifecycle events and heartbeats — share a **single global monotonic counter**. `event_id` values are globally unique across all job scopes and event types:

- Every call to `build_event()` increments the same module-level `_BROADCAST_COUNTER`, regardless of scope argument.
- Render lifecycle events (`render_queued`, `render_started`, `render_progress`, `render_completed`, `render_failed`, `render_cancelled`, `render_frame_available`) no longer restart at `event-00000` for each job — they receive the next globally unique id.
- Heartbeats are broadcast via `manager.broadcast()` (since BL-356) and enter the replay buffer with globally unique `event_id` values.

**Consequence for agents:** `event_id` values are globally monotonic and unambiguous as replay anchors. Persist the last received `event_id` from **any** event (including heartbeats) as the `Last-Event-ID` header on reconnect — the server returns every buffered event strictly after that id, with no cross-scope collision risk (see `src/stoat_ferret/api/websocket/manager.py:125-157`).

---

## Quick Reference Table

24 event types are defined. `Captured` rows below were observed live during v042 validation (see `Live Capture Evidence` at the end of this doc); all others are inferred from the emission site cited in the table.

| # | `type` | Domain | Terminal | Scope | Status | Emitted from |
|---|--------|--------|----------|-------|--------|--------------|
| 1 | `health_status` | Meta | n/a | global | Reserved (no emitter) | `events.py:24` |
| 2 | `heartbeat` | Meta | No | global | Captured | `api/routers/ws.py:26` |
| 3 | `scan_started` | Library | No | global | Captured | `api/services/scan.py:113` |
| 4 | `scan_completed` | Library | **Yes** | global | Captured | `api/services/scan.py:142-147` |
| 5 | `project_created` | Project | No | global | Captured | `api/routers/projects.py:150-155` |
| 6 | `timeline_updated` | Timeline | No | global | Inferred | `api/routers/timeline.py:259, 387, 482, 537` |
| 7 | `layout_applied` | Composition | No | global | Inferred | `api/routers/compose.py:212-217` |
| 8 | `audio_mix_changed` | Audio | No | global | Inferred | `api/routers/audio.py:193-198` |
| 9 | `transition_applied` | Timeline | No | global | Inferred | `api/routers/timeline.py:706-710, 833-837` |
| 10 | `job_progress` | Async jobs | **Yes** when `status == "complete"` | global | Captured | `api/services/scan.py:104-109, 150-155`; `api/services/proxy_service.py:498-509`; `api/services/waveform.py:582-593`; `api/services/thumbnail.py:567-578` |
| 11 | `preview.generating` | Preview (HLS) | No | global | Inferred | `preview/manager.py:317` |
| 12 | `preview.ready` | Preview (HLS) | **Yes** | global | Inferred | `preview/manager.py:400, 569` |
| 13 | `preview.seeking` | Preview (HLS) | No | global | Inferred | `preview/manager.py:504` |
| 14 | `preview.error` | Preview (HLS) | **Yes** | global | Inferred | `preview/manager.py:423, 585` |
| 15 | `ai_action` | AI / agents | n/a | global | Reserved (no emitter) | `events.py:38` |
| 16 | `render_queued` | Render | No | global | Captured | `render/service.py:236` |
| 17 | `render_started` | Render | No | global | Captured | `render/service.py:238` |
| 18 | `render_progress` | Render | No | global | Inferred | `render/service.py:541-556` |
| 19 | `render_frame_available` | Render | No | global | Inferred | `render/service.py:575-586` |
| 20 | `render_completed` | Render | **Yes** | global | Inferred | `render/service.py:402` |
| 21 | `render_failed` | Render | **Yes** | global | Inferred | `render/service.py:442` |
| 22 | `render_cancelled` | Render | **Yes** | global | Inferred | `render/service.py:363` |
| 23 | `render_queue_status` | Render | No | global | Captured | `render/service.py:664-674` |
| 24 | `proxy.ready` | Proxy | **Yes** (per-video) | global | Inferred | `api/services/proxy_service.py:319-327` |

Inferred rows have payloads reconstructed from the emission site listed; the wire format is identical to captured events (the same `build_event` helper is used). Mark any field discrepancy as a documentation bug.

> **Reserved** entries (`health_status`, `ai_action`) are present in the `EventType` enum but have no live emitter as of v042. Agents should accept and ignore them; do not depend on them.

---

## Per-Event Detail

All payload keys are JSON; `string`/`number`/`boolean`/`null`/`object` follow JSON conventions. Field types are described in TypeScript-flavoured shorthand (`string?` denotes optional / nullable).

### `heartbeat`

Connection liveness ping broadcast via `ConnectionManager.broadcast` (since BL-356). As a result:

- Heartbeats **are written to the replay buffer** (same path as all other broadcast events).
- Reconnects with `Last-Event-ID` will replay buffered heartbeats just like any other event.
- Heartbeat `event_id` values are globally unique and valid as `Last-Event-ID` replay anchors.

```jsonc
{ "type": "heartbeat", "payload": {}, "correlation_id": null,
  "timestamp": "2026-04-26T17:24:27.055733+00:00", "event_id": "event-00001" }
```

Interval: `STOAT_WS_HEARTBEAT_INTERVAL` seconds (default `30`). See `api/routers/ws.py:17-26`.

### `scan_started`

Emitted once per scan request after the handler accepts the path.

| Field | Type | Notes |
|-------|------|-------|
| `path` | string | Source directory passed in the scan request. |

```jsonc
{ "type": "scan_started",
  "payload": { "path": "C:/Users/.../scan_target" },
  "correlation_id": null,
  "timestamp": "2026-04-26T17:24:37.020392+00:00",
  "event_id": "event-00002" }
```

State transition: `scan job: pending → running` (the scan handler sets queue progress before broadcasting).

### `scan_completed` *(terminal)*

Emitted once per scan request after the directory walk completes successfully. Followed immediately by a final `job_progress` with `status == "complete"`.

| Field | Type | Notes |
|-------|------|-------|
| `path` | string | Echo of the input path. |
| `video_count` | integer | `result.new + result.updated` from the `ScanResponse`. |

```jsonc
{ "type": "scan_completed",
  "payload": { "path": "C:/.../scan_target", "video_count": 0 },
  "correlation_id": null,
  "timestamp": "2026-04-26T17:24:37.712217+00:00",
  "event_id": "event-00004" }
```

Failures are surfaced via the terminal `job_progress` `status` instead of a dedicated `scan_failed` event — there is no `scan_failed` type.

### `project_created`

Emitted on successful `POST /api/v1/projects`.

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | string | UUID of the new project. |
| `name` | string | Project name from the request body. |

```jsonc
{ "type": "project_created",
  "payload": { "project_id": "35e76266-…", "name": "v042-vocab-test" },
  "correlation_id": "a2f042be-…",
  "timestamp": "2026-04-26T17:24:06.868483+00:00",
  "event_id": "event-00000" }
```

### `timeline_updated`

Fan-out event for any timeline mutation: track replacement (`POST /api/v1/projects/{id}/timeline`), clip add (`POST /api/v1/projects/{id}/clips`), clip update (`PATCH /api/v1/projects/{id}/timeline/clips/{clip_id}`), or clip removal.

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | string | The affected project. |
| `clip_id` | string? | Present on add / update / remove; absent on the bulk track-replacement broadcast. |

Schema inferred from `api/routers/timeline.py:259, 387, 482, 537`.

### `layout_applied`

Emitted on `POST /api/v1/projects/{project_id}/compose/layout` when a multi-input layout preset is applied.

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | string | The affected project. |
| `preset` | string | Preset name (e.g. `"side_by_side"`, `"pip"`). |

Schema inferred from `api/routers/compose.py:212-217`.

### `audio_mix_changed`

Emitted on `POST /api/v1/projects/{project_id}/audio/mix` after the mix is persisted.

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | string | The affected project. |
| `tracks_configured` | integer | Number of tracks in the new mix. |

Schema inferred from `api/routers/audio.py:193-198`.

### `transition_applied`

Emitted on transition add (`POST /api/v1/projects/{id}/timeline/transitions`) and on transition delete (`DELETE …/transitions/{transition_id}`).

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | string | The affected project. |
| `transition_id` | string | Identifier of the transition added or removed. |

Schema inferred from `api/routers/timeline.py:706-710, 833-837`.

### `job_progress`

Generic async-job progress event used by **multiple subsystems**. The `payload.status` field drives the terminal-state semantics:

| `status` value | Meaning | Terminal? |
|----------------|---------|-----------|
| `"running"` | Job is in progress. | No |
| `"complete"` | Job reached terminal success. | **Yes** |
| `"failed"` | Job reached terminal failure (proxy/waveform/thumbnail subsystems). | **Yes** |
| `"generating"` | Proxy/waveform-style intermediate state. | No |

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Job identifier (the `job_id` returned by the originating async POST). |
| `progress` | number | `0.0`–`1.0` inclusive. |
| `status` | string | One of the values above. |
| `job_type` | string? | `"waveform"` or `"thumbnail_strip"` for those subsystems; absent on scan/proxy progress. |
| `proxy_quality` | string? | Present on proxy progress. |
| `target_resolution` | string? | Present on proxy progress (e.g. `"480x270"`). |
| `waveform_id` / `strip_id` / `video_id` | string? | Present on waveform / thumbnail progress for correlation. |

Captured (scan):

```jsonc
{ "type": "job_progress",
  "payload": { "job_id": "37a582b0-…", "progress": 1.0, "status": "running" },
  "correlation_id": null,
  "timestamp": "2026-04-26T17:24:37.711429+00:00",
  "event_id": "event-00003" }
```

```jsonc
{ "type": "job_progress",
  "payload": { "job_id": "37a582b0-…", "progress": 1.0, "status": "complete" },
  "correlation_id": null,
  "timestamp": "2026-04-26T17:24:37.712318+00:00",
  "event_id": "event-00005" }
```

> **Render note:** the render service does not emit `job_progress`; it emits `render_progress` instead. Treat the two streams as disjoint.

Sources: `api/services/scan.py:104-109,150-155`; `api/services/proxy_service.py:498-509`; `api/services/waveform.py:582-593`; `api/services/thumbnail.py:567-578`.

### `preview.generating`

HLS preview pipeline transitioned a session into `GENERATING` (FFmpeg started).

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | string | Preview session identifier. |

Schema inferred from `preview/manager.py:175-187, 317`.

### `preview.ready` *(terminal)*

HLS manifest is available at `session.manifest_path`. Also emitted on successful seek completion.

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | string | Preview session identifier. |

Schema inferred from `preview/manager.py:400, 569`.

### `preview.seeking`

Emitted when a seek request begins re-generating the manifest.

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | string | Preview session identifier. |

Schema inferred from `preview/manager.py:504`.

### `preview.error` *(terminal)*

Emitted when the HLS pipeline fails (FFmpeg error or seek failure).

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | string | Preview session identifier. |
| `error` | string | Truncated error message (≤500 chars). |

Schema inferred from `preview/manager.py:423, 585`.

### `render_queued`

Emitted when `RenderService.submit_job` enqueues a job. First render lifecycle event; carries the next globally-unique `event_id` (not `event-00000` — the global counter advances monotonically).

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Render job UUID. Same as `RenderJobResponse.id`. |
| `project_id` | string | Owning project. |
| `status` | string | Always `"queued"` at this point (`RenderStatus.value`). |

```jsonc
{ "type": "render_queued",
  "payload": { "job_id": "2c4763b8-…",
               "project_id": "35e76266-…",
               "status": "queued" },
  "correlation_id": "9bab51d4-…",
  "timestamp": "2026-04-26T17:24:55.055181+00:00",
  "event_id": "event-00000" }
```

### `render_started`

Immediately follows `render_queued` from `RenderService.submit_job`. Note: the `status` field still reads `"queued"` at broadcast time — the worker has not yet transitioned the job. Do not infer running from this event alone.

```jsonc
{ "type": "render_started",
  "payload": { "job_id": "2c4763b8-…",
               "project_id": "35e76266-…",
               "status": "queued" },
  "correlation_id": "9bab51d4-…",
  "timestamp": "2026-04-26T17:24:55.056935+00:00",
  "event_id": "event-00001" }
```

Schema captured.

### `render_progress`

Throttled progress emissions during an active render (max 1 per 0.5s, ≥5% delta, plus a guaranteed final `1.0` frame). See `render/service.py:494-556`.

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Render job UUID. |
| `progress` | number | `0.0`–`1.0`. |
| `eta_seconds` | number? | Estimated time remaining; nullable when unknown. |
| `speed_ratio` | number? | Render speed relative to real-time; nullable. |
| `frame_count` | integer? | Per-segment FFmpeg frame counter (resets on segment boundaries — **not** cumulative). |
| `fps` | number? | Current encoder FPS. |
| `encoder_name` | string? | e.g. `"libx264"`, `"h264_nvenc"`. |
| `encoder_type` | string? | `"HW"` or `"SW"`. |

Schema inferred from `render/service.py:541-556`.

### `render_frame_available`

Emitted up to ~2 Hz while the render is producing output. Pairs with `GET /api/v1/render/{job_id}/frame_preview.jpg` for a 540p still.

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Render job UUID. |
| `frame_url` | string | Path-only URL: `"/api/v1/render/{job_id}/frame_preview.jpg"`. |
| `resolution` | string | Always `"540p"`. |
| `progress` | number | `0.0`–`1.0` snapshot. |

Schema inferred from `render/service.py:575-586`.

### `render_completed` *(terminal)*

Job finished successfully. Followed by a `render_queue_status` broadcast on the **global** scope.

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Render job UUID. |
| `project_id` | string | Owning project. |
| `status` | string | `"completed"` (`RenderStatus.COMPLETED.value`). |

Schema inferred from `render/service.py:392-402, 457-474`.

### `render_failed` *(terminal)*

Emitted only after retries are exhausted (`current.retry_count >= max_retries`). Transient retry attempts do **not** emit `render_failed` — they re-queue silently.

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Render job UUID. |
| `project_id` | string | Owning project. |
| `status` | string | `"failed"`. |

Schema inferred from `render/service.py:407-445, 457-474`. The job's `error_message` is persisted on the row (`GET /api/v1/jobs/{job_id}`) but is **not** included in the WebSocket payload.

### `render_cancelled` *(terminal)*

Emitted on successful `POST /api/v1/render/{job_id}/cancel` (or programmatic cancel via `RenderService.cancel`).

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Render job UUID. |
| `project_id` | string | Owning project. |
| `status` | string | `"cancelled"`. |

Schema inferred from `render/service.py:343-366, 457-474`.

### `render_queue_status`

Emitted after every render lifecycle transition (`render_queued`, `render_completed`, `render_failed`, `render_cancelled`) so dashboards can refresh queue depth without polling. Uses the global event-id counter (all events share the same counter since BL-356).

| Field | Type | Notes |
|-------|------|-------|
| `active_count` | integer | Number of currently running render workers. |
| `pending_count` | integer | Render jobs waiting in queue. |
| `max_concurrent` | integer | Worker concurrency cap (`Settings.render_max_concurrent_jobs`). |
| `max_queue_depth` | integer | Queue capacity. |

```jsonc
{ "type": "render_queue_status",
  "payload": { "active_count": 0, "pending_count": 28,
               "max_concurrent": 4, "max_queue_depth": 50 },
  "correlation_id": "9bab51d4-…",
  "timestamp": "2026-04-26T17:24:55.056735+00:00",
  "event_id": "event-00006" }
```

Schema captured.

### `proxy.ready` *(per-video terminal)*

Emitted when proxy generation finishes successfully for a `(video_id, quality)` pair. Followed by a `job_progress` `complete` for the same `job_id`.

| Field | Type | Notes |
|-------|------|-------|
| `video_id` | string | Source video UUID. |
| `quality` | string | Proxy quality preset (e.g. `"low"`, `"medium"`). |

Schema inferred from `api/services/proxy_service.py:319-327`.

### Reserved: `health_status`, `ai_action`

Defined in `EventType` (`events.py:24, 38`) but no live emitter exists in v042. Treat as forward-compatible placeholders: clients should accept and ignore frames with these `type` values.

---

## Replay Buffer Semantics

The replay buffer is implemented in `src/stoat_ferret/api/websocket/manager.py`. Behaviour summary for agents:

- **Single global deque.** All `broadcast()` traffic is appended to one `deque(maxlen=ws_replay_buffer_size)` (default `1000` — `STOAT_WS_REPLAY_BUFFER_SIZE`). There is no per-client filtering. Memory is `O(buffer_size)`, not `O(buffer_size × clients)`.
- **TTL.** On reconnect, events older than `ws_replay_ttl_seconds` (default `300`) are dropped before the `Last-Event-ID` lookup. An event with a missing or unparseable `timestamp` is treated as fresh (deliberate: a malformed timestamp must not silently drop the event).
- **`Last-Event-ID` lookup.** The fresh deque is scanned for an entry whose `event_id` matches the header value. If found, every event **strictly after** it is replayed. If not found (TTL eviction or never seen), every fresh event is replayed.
- **No header → no replay.** A reconnect without `Last-Event-ID` receives only live frames — buffered history is not pushed.
- **Heartbeats are buffered (since BL-356).** They are sent via `manager.broadcast()`, enter the global replay buffer, and their `event_id` values are valid `Last-Event-ID` anchors. After a long disconnect, reconnecting with a heartbeat's `event_id` returns only events strictly after that heartbeat.
- **Server restart loses the buffer.** It is in-memory only.
- **`active_jobs` includes render jobs (since BL-357).** `GET /api/v1/system/state` now surfaces render jobs in RUNNING/QUEUED state in `active_jobs` and excludes terminal generic jobs older than 300 seconds. This corrects the reconnect-recovery path documented in `operator-guide.md` §3 — the system/state endpoint is now a valid recovery surface for render state. For authoritative render terminal state after a long disconnect, also query `GET /api/v1/render/{job_id}`.

All `event_id` values are globally unique (single global counter since BL-356), so any buffered `event_id` — from any event type, including render lifecycle events and heartbeats — is an unambiguous replay anchor. The server returns every event strictly after the matching frame in deque order.

Captured replay (since BL-356, global counter):

```text
GET /ws  (Last-Event-ID: event-00006)
→ event-00007  (next frame in the global deque after event-00006)
→ event-00008  …
```

`event_id` values are globally monotonic — the replayed ids are always numerically greater than the anchor. Use the anchor's deque position, not numeric comparison, as the authoritative "strictly after" boundary (the server scans by identity match then returns the tail).

---

## Live Capture Evidence

The following frames were captured against a freshly-started v042 server using `scripts/examples/dump-ws-events.py` on 2026-04-26. **Note:** this capture predates the BL-356 global-counter fix. Render events in the capture show per-scope ids (`event-00000`, `event-00001`) that would overlap with global events in the same session. On current servers (v066+), render events carry globally-unique ids (continuing the global sequence rather than restarting at `event-00000`).

```jsonl
{"type":"project_created","payload":{"project_id":"35e76266-…","name":"v042-vocab-test"},"correlation_id":"a2f042be-…","timestamp":"2026-04-26T17:24:06.868483+00:00","event_id":"event-00000"}
{"type":"heartbeat","payload":{},"correlation_id":null,"timestamp":"2026-04-26T17:24:27.055733+00:00","event_id":"event-00001"}
{"type":"scan_started","payload":{"path":"C:/.../scan_target"},"correlation_id":null,"timestamp":"2026-04-26T17:24:37.020392+00:00","event_id":"event-00002"}
{"type":"job_progress","payload":{"job_id":"37a582b0-…","progress":1.0,"status":"running"},"correlation_id":null,"timestamp":"2026-04-26T17:24:37.711429+00:00","event_id":"event-00003"}
{"type":"scan_completed","payload":{"path":"C:/.../scan_target","video_count":0},"correlation_id":null,"timestamp":"2026-04-26T17:24:37.712217+00:00","event_id":"event-00004"}
{"type":"job_progress","payload":{"job_id":"37a582b0-…","progress":1.0,"status":"complete"},"correlation_id":null,"timestamp":"2026-04-26T17:24:37.712318+00:00","event_id":"event-00005"}
{"type":"render_queued","payload":{"job_id":"2c4763b8-…","project_id":"35e76266-…","status":"queued"},"correlation_id":"9bab51d4-…","timestamp":"2026-04-26T17:24:55.055181+00:00","event_id":"event-00000"}
{"type":"render_queue_status","payload":{"active_count":0,"pending_count":28,"max_concurrent":4,"max_queue_depth":50},"correlation_id":"9bab51d4-…","timestamp":"2026-04-26T17:24:55.056735+00:00","event_id":"event-00006"}
{"type":"render_started","payload":{"job_id":"2c4763b8-…","project_id":"35e76266-…","status":"queued"},"correlation_id":"9bab51d4-…","timestamp":"2026-04-26T17:24:55.056935+00:00","event_id":"event-00001"}
```

Events with no captured emission during v042 validation are flagged `Inferred` in the Quick Reference Table; their schemas come from the cited emission sites and use the same envelope as captured events.

---

## See Also

- [`operator-guide.md`](operator-guide.md) — compact API + state machine reference. The "WebSocket Connection" and "Render Lifecycle Events" sections summarise the high-level transitions that this vocabulary documents at the wire level.
- [`prompt-recipes.md`](prompt-recipes.md#5-websocket-event-monitoring-with-reconnect) — Recipe 5 is the long-poll companion: how to consume this event stream from an agent, with a worked `Last-Event-ID` reconnect sequence.
- [`api-usage-examples.md`](api-usage-examples.md) — error semantics for the HTTP requests that emit these events.
- [`scripts/examples/dump-ws-events.py`](../../scripts/examples/dump-ws-events.py) — runnable consumer used to capture the evidence above.
- OpenAPI state machine documentation (BL-278) — see `docs/design/05-api-specification.md` for state-transition diagrams that this vocabulary's terminal markings reference.
