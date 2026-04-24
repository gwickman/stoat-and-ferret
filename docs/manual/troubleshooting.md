# Runtime Troubleshooting Decision Trees

Decision trees for on-call engineers responding to runtime incidents
with a deployed stoat-and-ferret service. Installation and toolchain
issues live in [`docs/setup/05_troubleshooting.md`](../setup/05_troubleshooting.md)
— the trees below cross-link to that document where a remediation step
is shared.

Every diagnostic command was executed against a live local server
(app 0.3.0, core 0.1.0, git SHA `108f558`) on 2026-04-24 on Windows 11
(Git Bash) and reflects the real response shapes. All commands work
unchanged in bash / sh / Git Bash.

Base URL in all examples is `http://localhost:8765`; override via
`STOAT_API_HOST` / `STOAT_API_PORT`. `STOAT_HOST` and `STOAT_PORT` are
honored by `scripts/deploy_smoke.sh` only — not by the server itself.

---

## How to use this document

1. Identify the symptom in the table of contents.
2. Run the **Diagnose** commands from the relevant tree, top to bottom.
3. Follow whichever branch matches the response.
4. Apply the **Resolve** step. If the step has a deeper remediation in
   [`docs/setup/05_troubleshooting.md`](../setup/05_troubleshooting.md)
   (e.g., FFmpeg installation, Rust import errors), follow the link
   rather than duplicating steps here.

## Contents

- [Tree 1: `/health/ready` reports failure or 503](#tree-1-health-check-failure)
- [Tree 2: Stuck render jobs (queued for >5 min)](#tree-2-stuck-render-jobs)
- [Tree 3: WebSocket clients repeatedly disconnect](#tree-3-websocket-disconnections)
- [Tree 4: Container startup takes >30 seconds](#tree-4-container-startup-slow)
- [Tree 5: High latency on `/api/v1/system/state`](#tree-5-high-latency-on-system-state)

---

## Tree 1: Health check failure

**Symptom:** `/health/ready` returns HTTP 503, or HTTP 200 with
`status: "unhealthy"`, or a specific subsystem reports `status:
"error"` / `status: "degraded"` in the `checks` block.

### Diagnose

```bash
curl -sw "\n%{http_code}\n" http://localhost:8765/health/ready
```

Parse the response. The four **critical** checks (`database`,
`ffmpeg`, `rust_core`, `filesystem`) gate `ready` — any of them being
non-ok flips the probe to HTTP 503. Three **non-critical** checks
(`preview`, `proxy`, `render`) can be `degraded` without dropping
`ready: true`.

```bash
# Extract just the checks block for readability.
curl -s http://localhost:8765/health/ready | python -c "import json,sys; print(json.dumps(json.load(sys.stdin)['checks'], indent=2))"
```

### Branches

**Branch 1a — `database.status != "ok"`.**

`checks.database.error` surfaces the underlying aiosqlite error.
Common causes:

- The database file is missing or the parent directory was never
  created — see [`docs/setup/05_troubleshooting.md`](../setup/05_troubleshooting.md#sqlalchemyexcoperationalerror-unable-to-open-database-file).
- Disk is full or the filesystem is read-only — `checks.filesystem`
  should also be non-ok.
- Long-lived lock held by a stale writer — inspect `lsof data/stoat.db`
  (POSIX) or the Sysinternals `handle` tool (Windows).

**Resolve:** Restore from the most recent
`data/backups/stoat_<timestamp>.db` (see
[Database procedures](runbook.md#database-procedures)) and restart.

**Branch 1b — `ffmpeg.status != "ok"`.**

`checks.ffmpeg.error` will typically be `ffmpeg not found in PATH` or
a timeout. Verify:

```bash
which ffmpeg          # POSIX
where ffmpeg          # Windows
ffmpeg -version       # should print a version banner
```

**Resolve:** Install FFmpeg or add its install directory to `PATH` —
follow [`docs/setup/05_troubleshooting.md`](../setup/05_troubleshooting.md#ffmpeg-not-found-in-path).
Restart the service after fixing `PATH`.

**Branch 1c — `rust_core.status != "ok"`.**

The Rust extension failed to load. `checks.rust_core.error` is the
import error. This is typically a build / installation fault, not a
runtime fault.

**Resolve:** Rebuild the extension (`uv run maturin develop`) and
restart. Follow the import-error remediation in
[`docs/setup/05_troubleshooting.md`](../setup/05_troubleshooting.md#runtimeerror-stoat_ferret_core-native-extension-not-built)
and the Windows DLL-load guide below it.

**Branch 1d — `filesystem.status != "ok"`.**

The database directory is not writable by the server process.

**Resolve:** `chmod` / `chown` the directory, or `mkdir -p data` if it
is missing. Inside containers, verify the volume mount is read-write
and the `uid/gid` of the mounted volume matches the runtime user.

**Branch 1e — Non-critical `degraded` (HTTP 200, `ready: true`).**

`proxy.proxy_dir_writable: false` in a fresh install is the most
common cause — the `data/proxies` directory is absent. The service
remains **ready**; the proxy feature is effectively disabled until
the directory exists.

```bash
mkdir -p data/proxies
curl -s http://localhost:8765/health/ready | python -c "import json,sys;d=json.load(sys.stdin);print(d['checks']['proxy'])"
# {'status': 'ok', 'proxy_dir_writable': True, 'pending_proxies': 0}
```

Other non-critical degradations:

- `render.status: "unavailable"` — FFmpeg missing. Same fix as
  Branch 1b.
- `render.status: "degraded"` with high `disk_usage_percent` — see
  [Tree 2: Stuck render jobs](#tree-2-stuck-render-jobs) for disk and
  queue tuning.
- `preview.cache_healthy: false` — preview cache >90% used; the cache
  self-evicts, no action needed unless sustained.

### Prevention

- Load balancers should require **`ready: true`** (JSON field) and
  **HTTP 200** together — neither alone is sufficient.
- Alert on HTTP 503 from `/health/ready` sustained >1 minute.
  Transient 503s during a slow SQLite `VACUUM` or a single FFmpeg
  probe timeout are expected and recoverable.

---

## Tree 2: Stuck render jobs

**Symptom:** A render job stays in `status: "queued"` for more than
about 5 minutes, or `/api/v1/render/queue` reports `pending_count >> 0`
with `active_count == 0`.

### Diagnose

```bash
curl -s http://localhost:8765/api/v1/render/queue | python -m json.tool
```

Captured response from the live run:

```json
{
  "active_count": 0,
  "pending_count": 26,
  "max_concurrent": 4,
  "max_queue_depth": 50,
  "disk_available_bytes": 385486131200,
  "disk_total_bytes": 1022000173056,
  "completed_today": 0,
  "failed_today": 0
}
```

List the queued jobs to confirm the age of the oldest one:

```bash
curl -s "http://localhost:8765/api/v1/render?status=queued&limit=5" | python -m json.tool
```

Each entry carries `created_at` / `updated_at` — compute age against
the server clock (the value in `/api/v1/version`'s `build_timestamp`
is compile-time only; for clock drift use the `Date` header from any
response).

### Branches

**Branch 2a — `active_count == 0` and the service was started with
`python -m stoat_ferret.api`.**

**This is the expected outcome.** A bare API process accepts render
submissions and exposes the full status/cancel/retry surface but does
not drive `RenderService.run_job(job, command)` — jobs will remain in
`queued` until an external caller (a future dedicated worker service,
an integration test, or a scripted hook) invokes the service.

**Resolve:** Wire a render worker in your deployment topology. In the
current supported configuration this is a deployment-time concern —
see the
[Render worker caveat in the runbook](runbook.md#render-worker-caveat).
To drain the backlog immediately, cancel the stale jobs:

```bash
for id in $(curl -s "http://localhost:8765/api/v1/render?status=queued&limit=50" | python -c "import json,sys; print('\n'.join(j['id'] for j in json.load(sys.stdin)['items']))"); do
  curl -s -X POST "http://localhost:8765/api/v1/render/$id/cancel" > /dev/null
done
```

**Branch 2b — `active_count == max_concurrent` and `pending_count > 0`.**

The queue is saturated — jobs are waiting for concurrency, not stuck.
`max_concurrent` is `STOAT_RENDER_MAX_CONCURRENT` (default 4, range
1–16). See
[Performance tuning](runbook.md#performance-tuning) for the raise
procedure.

**Resolve:** Raise `STOAT_RENDER_MAX_CONCURRENT`, or slow the
submission rate, or wait. No error — just backpressure.

**Branch 2c — `active_count > 0`, individual jobs show
`status: "running"` with no `progress` advancement.**

FFmpeg is running but not making progress.

```bash
# Linux / macOS
ps -eo pid,etimes,cmd | grep ffmpeg
# Windows (PowerShell)
powershell -c "Get-Process ffmpeg | Select-Object Id,StartTime,Responding"
```

A sustained `stoat_ferret_ffmpeg_active_processes` gauge with no
change in `stoat_ferret_ffmpeg_executions_total` confirms a hung
child.

**Resolve:** Cancel the job — cancellation sends `q` on stdin and
waits `STOAT_RENDER_CANCEL_GRACE_SECONDS` (default 10) before killing.
If FFmpeg routinely hangs on the same input, investigate the source
file and encoder combination in isolation with `ffmpeg -v verbose`.

**Branch 2d — `disk_available_bytes` is small relative to
`disk_total_bytes`, or `checks.render.status == "degraded"` on
`/health/ready`.**

The render output filesystem is over
`STOAT_RENDER_DISK_DEGRADED_THRESHOLD` (default 0.9). New jobs still
queue but the probe degrades.

**Resolve:** Free space on the render output volume
(`STOAT_RENDER_OUTPUT_DIR`, default `data/renders`) or point to a
different volume.

### Prevention

- Alert on `pending_count / max_queue_depth > 0.8` sustained for
  >5 minutes.
- Watch for render jobs older than `STOAT_RENDER_TIMEOUT_SECONDS`
  (default 3600) still in `queued` — they are candidates for
  cancellation rather than retry.

---

## Tree 3: WebSocket disconnections

**Symptom:** Clients connected to `/ws` reconnect repeatedly, report
missed events, or see the server-initiated close with reason text
mentioning `replay_buffer_exhausted` or a stale `Last-Event-ID`.

### Diagnose

```bash
# Snapshot the current WS state.
curl -s http://localhost:8765/api/v1/system/state | python -m json.tool
```

Real response:

```json
{
  "timestamp": "2026-04-24T09:02:48.471639Z",
  "active_jobs": [],
  "active_connections": 0,
  "uptime_seconds": 9.619042
}
```

Check the replay buffer utilization (exposed via `/health/ready`):

```bash
curl -s http://localhost:8765/health/ready | python -c "import json,sys;d=json.load(sys.stdin); print('ws_buffer_utilization:', d['ws_buffer_utilization'])"
```

Grep the log for connection churn:

```bash
grep '"logger": "stoat_ferret.api.websocket' logs/stoat-ferret.log | tail -20
```

### Branches

**Branch 3a — High reconnect rate with replay buffer at/near capacity.**

The WebSocket replay buffer is a **server-global deque** of size
`STOAT_WS_REPLAY_BUFFER_SIZE` (default 1000). When a client reconnects
with a `Last-Event-ID` older than the oldest retained event, replay
cannot catch it up — the client receives a full snapshot instead.

**Resolve:** Raise `STOAT_WS_REPLAY_BUFFER_SIZE`. Memory is
`O(buffer size)` globally (not per-client) so the trade-off is a
bounded amount of server RAM. See
[Performance tuning](runbook.md#performance-tuning).

Additionally raise `STOAT_WS_REPLAY_TTL_SECONDS` (default 300) if
clients commonly reconnect after gaps longer than 5 minutes —
otherwise buffered events are dropped by TTL before they can be
replayed.

**Branch 3b — `active_connections` drops to 0 then climbs, repeatedly.**

The server or the load balancer is terminating connections. Check:

- The heartbeat interval (`STOAT_WS_HEARTBEAT_INTERVAL`, default 30)
  is less than any intermediate proxy's idle timeout.
- Recent log lines for `deployment.startup` — if the server has been
  restarting, the loop is external to WebSocket handling.
- The load balancer's sticky-session setting — WS must not round-robin
  between replicas (replay buffers are per-process).

**Resolve:** Lower `STOAT_WS_HEARTBEAT_INTERVAL` below the proxy's
idle timeout (e.g., 20 s behind a nginx default of 60 s). Pin the
session to a single replica.

**Branch 3c — Single client fails to reconnect cleanly.**

Client-side bug. Confirm by connecting a known-good client
(`websocat ws://localhost:8765/ws`) and verifying it survives.

**Resolve:** File against the client; see the reconnect protocol in
[`docs/framework-context/FRAMEWORK_CONTEXT.md`](../framework-context/FRAMEWORK_CONTEXT.md#websocket-replay)
and the `useWebSocket` implementation under `gui/src/`.

### Prevention

- Alert on `active_connections` dropping by more than 50% within
  60 seconds when no deploy / restart is in flight.
- When planning a higher-fan-out deployment, size
  `STOAT_WS_REPLAY_BUFFER_SIZE` to `events_per_second × expected_gap_seconds`
  (client reconnect window) rather than to connection count.

---

## Tree 4: Container startup slow

**Symptom:** The container takes more than ~30 seconds between
`docker run` and `scripts/deploy_smoke.sh` returning success, or
`/health/ready` continues to return HTTP 503 with `status: "starting"`.

### Diagnose

```bash
# Inside the container (or via docker exec):
tail -f /app/logs/stoat-ferret.log

# From outside:
docker logs -f stoat-ferret
```

Look for the sequence (startup log events are listed in the
[runbook Startup sequence](runbook.md#what-happens-during-startup)):

1. `deployment.migration.*` (migration pass)
2. `deployment.feature_flag` (4 lines, one per flag)
3. `render_checkpoint.recovery`
4. `job_worker_started` / `worker_started`
5. `deployment.startup`

Time gaps between these events point at the slow step.

### Branches

**Branch 4a — Long gap before `deployment.migration.*`.**

The alembic migration is doing schema work. On first start against a
large pre-existing database this can take minutes. The lifespan
handler has already written the pre-migration backup to
`data/migration_backups/` — a failure here is recoverable.

**Resolve:** Wait. If the migration fails
(`deployment.migration.failed` log event), inspect the `error` field
and restore from the emitted `backup_path`. Do **not** add application
timeouts around the migration — a partial schema is worse than a slow
start.

**Branch 4b — Long gap before `render_checkpoint.recovery`.**

Render checkpoint recovery queries every `render_jobs` row in
interrupted state. On a database with thousands of terminal rows the
read is still bounded but first-page-warm I/O can stall.

**Resolve:** Prune old rows via `sqlite3 data/stoat.db
"DELETE FROM render_jobs WHERE status IN ('completed','failed','cancelled')
  AND completed_at < datetime('now', '-30 days')"` during a
maintenance window. (There is no automatic render-job retention
today.)

**Branch 4c — Long gap before `job_worker_started`.**

Effect registry initialization is slow. This points at a Rust-side
issue — `stoat_ferret_core` symbol loading should be milliseconds.

**Resolve:** Investigate with a Python stack sample
(`py-spy record -d 30 -- python -m stoat_ferret.api`); verify the
`.pyd` / `.so` file is on a fast disk (not a network mount).

**Branch 4d — `deployment.startup` emits promptly but
`/health/ready` still returns 503.**

A critical check is failing. Fall through to
[Tree 1: Health check failure](#tree-1-health-check-failure).

### Prevention

- Container liveness: use `/health/live` (not `/health/ready`) —
  `scripts/deploy_smoke.sh` already does this for a reason: slim
  production images intentionally omit FFmpeg in some deployments,
  which trips `/health/ready` into `degraded`.
- Kubernetes startup probe: target `/health/ready` with
  `initialDelaySeconds` high enough to cover a realistic migration
  pass on your largest-database deploy (conservative default: 60 s).

---

## Tree 5: High latency on system-state

**Symptom:** `GET /api/v1/system/state` routinely takes longer than
~300 ms, or the synthetic probe that reads the endpoint reports
SLO breaches.

### Diagnose

```bash
# Time a single call.
curl -s -o /dev/null -w "total=%{time_total}s http=%{http_code}\n" http://localhost:8765/api/v1/system/state
```

Observed on a clean local run:

```text
total=0.214810s http=200
```

Compare the histogram distribution in Prometheus:

```bash
curl -sL http://localhost:8765/metrics | grep 'http_request_duration_seconds_bucket{.*/api/v1/system/state'
```

### Branches

**Branch 5a — Latency scales with `active_jobs` length.**

The snapshot iterates the in-memory job queue. A large `active_jobs`
list means the job worker is falling behind or jobs are not being
drained.

```bash
curl -s http://localhost:8765/api/v1/system/state | python -c "import json,sys;d=json.load(sys.stdin); print('active_jobs:', len(d['active_jobs']), 'active_connections:', d['active_connections'])"
```

**Resolve:** Identify the job types and follow-through to the
relevant queue — render jobs to
[Tree 2](#tree-2-stuck-render-jobs); scan jobs by tailing the log for
`scan_requested` / `scan_completed` event pairs.

**Branch 5b — Latency scales with `active_connections`.**

`ws_manager.active_connections` is an O(1) read in normal operation,
but a contended lock can serialize the read. Check the log for
`system_state.ws_manager_unavailable` warnings.

**Resolve:** If the WS manager is repeatedly unavailable, the upstream
cause (memory pressure, GIL contention under heavy event fan-out) is
the real issue — profile with `py-spy` and inspect
`stoat_ferret_ffmpeg_active_processes` for contemporaneous render
spikes.

**Branch 5c — Latency is elevated across every endpoint, not just
`/api/v1/system/state`.**

The endpoint itself is not the bottleneck. Check:

- Host CPU / memory saturation (`top`, `docker stats`).
- FFmpeg process count (`stoat_ferret_ffmpeg_active_processes`).
- Disk I/O (renders may be I/O bound on the output volume).

**Resolve:** This is a capacity / topology issue rather than a code
issue. Reduce `STOAT_RENDER_MAX_CONCURRENT` (see
[Performance tuning](runbook.md#performance-tuning)) or scale the
host. `/api/v1/system/state` is guaranteed to do no database I/O (see
the INV-SNAP-1 invariant in `src/stoat_ferret/api/routers/system.py`),
so raw endpoint tuning will not help.

### Prevention

- Alert on p95 of
  `http_request_duration_seconds{path="/api/v1/system/state"}`
  exceeding 500 ms for >5 minutes.
- Remember that this endpoint is the WebSocket bootstrap snapshot —
  latency here translates directly into client boot time.

---

## Escalation

If a tree above does not match or the resolution does not restore
service, collect:

- Full `/health/ready` response (including all `checks`).
- Last 200 lines of `logs/stoat-ferret.log` (JSON-formatted).
- `/api/v1/version` response.
- `/api/v1/system/state` response.
- `/api/v1/render/queue` response.
- Output of `curl -sL http://localhost:8765/metrics | wc -l` and any
  `# HELP` lines that diverge from the reference list in the
  [runbook Prometheus metrics section](runbook.md#prometheus-metrics).

These together are sufficient for an engineer unfamiliar with the
deployment to reconstruct the incident timeline.
