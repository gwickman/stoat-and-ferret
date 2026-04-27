# API Operator Guide

Compact reference for AI agents operating stoat-and-ferret over HTTP/WebSocket. Happy-path only; see `api-usage-examples.md` for error handling and `ws-event-vocabulary.md` for event payloads.

## API Orientation

- **Base URL**: `http://localhost:8765` (default; `STOAT_API_HOST`/`STOAT_API_PORT`).
- **Auth**: None in dev. Production deployments terminate TLS + auth at a reverse proxy.
- **Content-Type**: `application/json` for all POST/PATCH bodies.
- **Spec**: `GET /openapi.json` returns the live OpenAPI schema.
- **Liveness / readiness**: `GET /health/live`, `GET /health/ready` (no `/api/v1` prefix).
- **Core surface**: `/api/v1/videos`, `/api/v1/projects`, `/api/v1/render`, `/api/v1/jobs/{job_id}`, `/ws`.

## Canonical Sequences

### 1. Scan → Project → Timeline → Render

Async jobs return `202 Accepted` with `{"job_id": ...}`. Poll or long-poll to completion; sync writes return `200/201` with the resource.

| Step | Request | Success | Result |
|------|---------|---------|--------|
| Scan library | `POST /api/v1/videos/scan` `{"path": "/abs/path", "recursive": true}` | 202 `{job_id}` | background job |
| Wait for scan | `GET /api/v1/jobs/{job_id}/wait?timeout=30` | 200 `{status, result}` | `result.scanned/new/updated` |
| List videos | `GET /api/v1/videos` | 200 `{videos: [...]}` | pick `video_id` |
| Create project | `POST /api/v1/projects` `{"name": "demo", "output_width": 1920, "output_height": 1080, "output_fps": 30}` | 201 project | `id` |
| Add timeline clip | `POST /api/v1/projects/{project_id}/timeline/clips` `{"video_id", "start_time", "duration"}` | 201 clip | `id` |
| Apply effect | `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` `{"name", "parameters": {...}}` | 201 effect | applied |
| Start render | `POST /api/v1/render` `{"project_id", "output_format": "mp4", "quality_preset": "standard"}` | 201 `{id, status}` | render job id |
| Wait for render | `GET /api/v1/jobs/{job_id}/wait?timeout=300` | 200 terminal status | `status == complete` → `output_path` |

### 2. WebSocket + Reconnect

1. Connect: `WS ws://localhost:8765/ws`. Server pushes one-way JSON.
2. Each event has shape `{event_id, type, payload, correlation_id?, timestamp}` (ids are monotonic per `job_id` scope, e.g. `event-00042`).
3. Persist the latest `event_id` you processed.
4. On reconnect, send HTTP header `Last-Event-ID: <last_event_id>` during the WebSocket handshake — the server replays buffered events strictly newer than that id (TTL `ws_replay_ttl_seconds`, drops `heartbeat`). If the id is missing from the buffer, you receive all still-buffered events.
5. Heartbeats arrive as `type: "heartbeat"` and are excluded from replay; ignore for state reconstruction.

### 3. State Snapshot

- `GET /api/v1/system/state` → `{timestamp, active_jobs: [...], active_connections, uptime_seconds}`. Poll on reconnect to reconcile jobs that terminated outside the replay window.

## State Machines

### Async Job (scan, render)

`pending → running → complete` (terminal, success) or `pending → running → failed` (terminal, error). Additional terminal states: `cancelled`, `timeout`. Progress is `0.0 – 1.0` on `GET /api/v1/jobs/{job_id}` and `result` populates on `complete`. Transitions never reverse.

### WebSocket Connection

`connect → (replay Last-Event-ID → ) live → disconnect`. Replay runs exactly once at accept time; subsequent frames are live broadcasts. On disconnect, buffered events survive for TTL; server restart loses the buffer — use `GET /api/v1/system/state` as the durable fallback.

### Render Lifecycle Events

`render_queued → render_started → render_progress (*) → render_completed | render_failed | render_cancelled`. Poll `GET /api/v1/jobs/{job_id}` or `GET /api/v1/render/{job_id}` for authoritative status; WebSocket events are best-effort.

## Testing Mode

Enable fixtures by starting the server with `STOAT_TESTING_MODE=true`. Endpoints return `403 TESTING_MODE_DISABLED` otherwise.

- Seed: `POST /api/v1/testing/seed` `{"fixture_type": "project", "name": "demo", "data": {...}}` → `{fixture_id, fixture_type, name}`. All seeded names are prefixed `seeded_` for enumeration.
- Teardown: `DELETE /api/v1/testing/seed/{fixture_id}?fixture_type=project`.
- Canonical agent test loop: seed project → add timeline clip → POST `/api/v1/render` with `render_plan: "dry_run"` → assert `status == complete` without writing output → delete fixture.
- Fixtures live in the same SQLite database as production data; use a dedicated `STOAT_DATA_DIR` for isolation.

### Synthetic render mode (`STOAT_RENDER_MODE`)

`STOAT_RENDER_MODE` selects how the render service treats incoming jobs:

- `real` (default): real FFmpeg execution; `POST /api/v1/render` requires `ffmpeg` on `PATH` or returns `503 RENDER_UNAVAILABLE`.
- `noop`: synthetic short-circuit. The render service still validates the request, enqueues the job, and broadcasts `render_queued` / `render_started` / `render_completed`, but no FFmpeg process is spawned. `ffmpeg_available` is forced to `True` so the load-test harness can run on hosts without FFmpeg installed.

Reserved for load testing (see `docs/benchmarks/load-test-results.md` and `tests/loadtests/locustfile.py`). Unknown values are rejected at startup. Production deployments must keep `STOAT_RENDER_MODE` unset (or `real`).

## When to Add an MCP Abstraction (vs. direct HTTP)

Stay on direct HTTP + this guide until **two or more** of the following apply; then introduce an MCP server under `mcp/` and expose typed tools.

- Agents repeatedly reconstruct the same 3+ step sequence (e.g. scan → project → render) from this guide each session.
- A sequence requires stateful correlation (`event_id` bookkeeping, `job_id` → `render_id` handoff) that agents get wrong without typed helpers.
- More than one agent runtime (Claude, GPT, custom) needs the same workflow and copy-pasting curl invocations drifts.
- Response payloads exceed an agent's context budget and need server-side filtering.

Single-call endpoints (health checks, state snapshot, one-shot seeds) do not justify MCP; prefer `curl` / `fetch`.

## Further Reading

- Full endpoint catalogue: `docs/manual/03_api-reference.md`
- Runnable recipes: `docs/manual/prompt-recipes.md`, `scripts/examples/`
- Event payloads: `docs/manual/ws-event-vocabulary.md`
- Error handling, retries, auth in production: `docs/manual/api-usage-examples.md`
