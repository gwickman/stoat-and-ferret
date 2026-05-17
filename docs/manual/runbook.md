# Operational Runbook

Operator-facing reference for starting, stopping, backing up, and
monitoring the stoat-and-ferret service. Every command below was
executed against a locally-built server (app 0.3.0, core 0.1.0, git SHA
`108f558`) on 2026-04-24 on Windows 11 (Git Bash). Paths use forward
slashes and work unchanged on Linux, macOS, and Windows Git Bash.

For the underlying configuration reference see
[`docs/setup/04_configuration.md`](../setup/04_configuration.md) — it is
the **single source of truth** for all `STOAT_*` environment variables
and their defaults. Tuning values quoted in this runbook are links back
into that file rather than duplicated tables.

For the development setup and prerequisites see
[`docs/setup/02_development-setup.md`](../setup/02_development-setup.md);
for installation / OS-specific build issues see
[`docs/setup/05_troubleshooting.md`](../setup/05_troubleshooting.md).
For runtime failure symptoms see the companion
[`docs/manual/troubleshooting.md`](troubleshooting.md) decision trees.

---

## Audience and scope

This runbook targets:

- **Operators** deploying the service to a host or container.
- **On-call engineers** responding to alerts or user-reported incidents.
- **Release engineers** verifying a deployment before handing off.

It covers:

- Startup and graceful shutdown.
- Database backup, restore, and migrations.
- Log file locations and rotation.
- Performance tuning entry points.
- Container deployment checklist.
- Prometheus metrics endpoint and key signals.

It **does not** cover development workflows, editor usage, or
architecture rationale — those live in `docs/manual/` (user guides) and
`docs/design/` (architecture specs).

---

## Startup sequence

The service exposes `/health/live` as a minimal liveness probe and
`/health/ready` as a deep readiness probe. Neither endpoint is under
the `/api/v1` prefix — this is intentional for load-balancer
compatibility.

### Start the service

```bash
# Default — binds 127.0.0.1:8765
uv run python -m stoat_ferret.api

# Override host / port via env
STOAT_API_HOST=0.0.0.0 STOAT_API_PORT=9000 uv run python -m stoat_ferret.api
```

### What happens during startup

The lifespan handler runs the following steps in order. Each step
emits a structured log line so a failure is discoverable in
`logs/stoat-ferret.log` (see [Log locations](#log-locations-and-rotation)).

1. **Migration safety.** A pre-migration SQLite backup is written to
   `data/migration_backups/migration_<ISO-timestamp>.db` (the directory
   is governed by `STOAT_MIGRATION_BACKUP_DIR`, default
   `data/migration_backups`), then pending alembic migrations are
   applied. If the database is already current the log line is
   `deployment.migration.already_current`.
2. **Feature flag audit.** One `deployment.feature_flag` log line per
   `STOAT_*` flag, plus an append-only row in the `feature_flag_log`
   SQLite table.
3. **Render checkpoint recovery.** Any interrupted render jobs are
   resumed from their last checkpoint — logged as
   `render_checkpoint.recovery` and `render_service.recovery_complete`.
4. **Job worker and effect registry initialization.** Logged as
   `job_worker_started` and `worker_started`.
5. **Startup gate opens.** A single `deployment.startup` log event
   records the final `app_version`, `core_version`, `git_sha` (runtime-resolved),
   and `sqlite_version` that were loaded. The `git_sha` in this event reflects
   the running code identity (same value as `app_sha` in `/api/v1/version`).

Expected log tail on a clean start (newest entries last):

```json
{"event":"job_worker_started","level":"info","logger":"stoat_ferret.api.app",...}
{"event":"worker_started","level":"info","logger":"stoat_ferret.jobs.queue",...}
{"app_version":"0.3.0","core_version":"stoat_ferret_core OK","git_sha":"108f558","sqlite_version":"3.50.4","event":"deployment.startup","level":"info",...}
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
```

Until `deployment.startup` is emitted the readiness probe returns 503
with `status: "starting"` — load balancers should wait for a 200 before
directing traffic.

### Verify readiness

```bash
curl -s http://localhost:8765/health/live
# {"status":"ok"}

curl -s http://localhost:8765/health/ready
```

Captured `/health/ready` response on a clean local run:

```json
{
  "ready": true,
  "status": "degraded",
  "app_version": "0.3.0",
  "sqlite_version": "3.50.4",
  "core_version": "stoat_ferret_core OK",
  "ws_buffer_utilization": 0.0,
  "uptime_seconds": 90.56,
  "checks": {
    "database":   {"status": "ok", "latency_ms": 0.47, "version": "3.50.4"},
    "ffmpeg":     {"status": "ok", "version": "8.0.1-full_build-www.gyan.dev"},
    "rust_core":  {"status": "ok", "version": "stoat_ferret_core OK"},
    "filesystem": {"status": "ok"},
    "preview":    {"status": "ok", "active_sessions": 0, "cache_healthy": true},
    "proxy":      {"status": "degraded", "proxy_dir_writable": false, "pending_proxies": 0},
    "render":     {"status": "ok", "encoder_available": true, "active_jobs": 0}
  }
}
```

**Readiness interpretation:**

- `ready: true` is the single field a load balancer should care about.
  Only the four **critical** checks (`database`, `ffmpeg`, `rust_core`,
  `filesystem`) flip `ready` to `false` and force HTTP 503.
- `status` is a three-way summary: `ok` when every check is green,
  `degraded` when a non-critical check is not green but the service is
  still ready, and `degraded` (with HTTP 503) when a critical check
  fails.
- The **degraded** state is expected in a dev environment when the
  `data/proxies` directory is missing (`proxy_dir_writable: false`).
  See the
  [troubleshooting decision tree for `/health/ready` failures](troubleshooting.md#tree-1-health-check-failure)
  for the full set of known-degraded conditions.
- The live reference for the schema is the `HealthStatus` model in
  `src/stoat_ferret/models/health.py` and the handler in
  `src/stoat_ferret/api/routers/health.py`.

Known degraded conditions that do **not** require operator action
(documented so on-call does not chase them):

| Symptom | Cause | Remediation |
|---------|-------|-------------|
| `proxy.proxy_dir_writable: false` | `data/proxies` is missing or read-only | `mkdir -p data/proxies` — or accept if proxy generation is not used |
| `preview.cache_healthy: false` | Preview cache is >90% full | Preview cache is self-evicting; no action needed unless sustained |
| `render.status: "unavailable"` | `ffmpeg` is not on `PATH` inside the server process | Install FFmpeg or add the install dir to `PATH` — see the installation [troubleshooting guide](../setup/05_troubleshooting.md#ffmpeg-not-found-in-path) |
| `render.status: "degraded"` with high `queue_depth` | Sustained submission rate exceeds `STOAT_RENDER_MAX_CONCURRENT` | Raise the concurrency knob or slow the submitter |

### Post-deployment smoke test

For deployed environments, use the provided smoke script instead of
hand-running curl:

```bash
bash scripts/deploy_smoke.sh
# STOAT_HOST=stoat.example.com STOAT_PORT=8765 bash scripts/deploy_smoke.sh
```

The script polls `/health/live` (not `/health/ready`, which trips
degraded on missing FFmpeg in slim container images) until it returns
200, then verifies `/api/v1/version` returns valid JSON with
`app_version`. Exit code is 0 on pass, 1 on failure.

Expected output:

```text
Waiting for http://localhost:8765 to be ready (max 60s)...
✓ /health/live returned 200
Verifying /api/v1/version...
✓ /api/v1/version returned valid JSON with app_version
✓ Deployment smoke test passed
```

---

## Graceful shutdown

Send `SIGTERM` (Ctrl+C when running in the foreground). The lifespan
handler runs a deterministic teardown sequence designed to avoid
half-finished renders, corrupt database state, or leaked FFmpeg
children.

### Sequence

1. **Synthetic monitoring task cancelled.** Prevents late probes from
   racing with shutdown.
2. **Render service stop-the-world.**
   1. `RenderService.initiate_shutdown()` — new render submissions are
      rejected with 503 `RENDER_UNAVAILABLE`.
   2. `RenderExecutor.cancel_all()` — active FFmpeg processes receive
      `q` on stdin for graceful finalize.
   3. Wait `STOAT_RENDER_CANCEL_GRACE_SECONDS` (default 10) for
      FFmpeg to flush its muxer — logged as
      `render_shutdown.waiting_grace`.
   4. Any stragglers are killed — logged as
      `render_shutdown.killed_remaining` (warning level).
   5. Temp files are cleaned — logged as
      `render_shutdown.temp_files_cleaned`.
3. **Preview sessions cancelled, preview cache cleanup task stopped.**
4. **Job worker cancelled, aiosqlite connection closed.**

### Command reference

```bash
# Foreground process: Ctrl+C sends SIGINT which is handled identically to SIGTERM.

# Background / daemon: find the PID and send SIGTERM.
pkill -TERM -f "stoat_ferret.api"

# After SIGTERM, give the process at least STOAT_RENDER_CANCEL_GRACE_SECONDS
# (default 10) seconds before SIGKILL. Longer grace is required for large
# renders — bump the env var before deploy, not during shutdown.

# Confirm the process is gone (POSIX).
ps aux | grep stoat_ferret.api | grep -v grep
# Windows (Git Bash):
tasklist | grep -i python
```

### What to check after shutdown

- `logs/stoat-ferret.log` tail ends with `job_worker_stopped` — if it
  ends earlier the teardown was aborted and operator review of the
  render output directory for orphan temp files (`*.part*.mp4`) is
  recommended.
- No residual `ffmpeg` processes. A healthy shutdown does not leave
  any — if `render_shutdown.killed_remaining` appears in the log, a
  future render with the same `output_path` will need manual cleanup.

---

## Database procedures

stoat-and-ferret uses a single SQLite database. The path is governed
by `STOAT_DATABASE_PATH` (default `data/stoat.db`). See
[`docs/setup/04_configuration.md#database`](../setup/04_configuration.md#database)
for the full list of database-related env vars.

### Fixture vs runtime database

There are two distinct database states:

- **Seed fixture** (`tests/fixtures/stoat.seed.db`) — immutable, tracked in git,
  contains the baseline schema with seed data. Never modified at runtime.
- **Runtime database** (`data/stoat.db`) — ephemeral, gitignored, created fresh
  on first server start if absent.

**Bootstrap behaviour:** On startup, if `data/stoat.db` does not exist, the server
automatically copies `tests/fixtures/stoat.seed.db` to `data/stoat.db` and runs
Alembic migrations to bring the schema to the current head. Subsequent starts
reuse the existing runtime database and apply only pending migrations (a no-op
when the schema is already current).

Because `data/stoat.db` is gitignored, `git pull` never touches the runtime
database. See the developer setup guide
([`docs/setup/02_development-setup.md`](../setup/02_development-setup.md#initialize-the-database))
for the developer-facing explanation of this model.

### Routine backup

Backups are taken from the **runtime database** (`data/stoat.db`). The seed
fixture (`tests/fixtures/stoat.seed.db`) is tracked in git and does not need
to be backed up by operators — restore it by running `git checkout` if it is
accidentally modified.

SQLite backups must be taken with a tool that understands the
write-ahead log (`stoat.db-wal` / `stoat.db-shm`). A plain file copy of
`stoat.db` while the service is running can miss committed transactions
or capture an inconsistent page state.

```bash
# Preferred: use sqlite3 .backup which is safe against a live writer.
# This targets the runtime database, not the seed fixture.
sqlite3 data/stoat.db ".backup 'data/backups/stoat_$(date -u +%Y%m%dT%H%M%SZ).db'"
```

For scheduled backups, run the command on an interval (cron, systemd
timer, or an external scheduler). The resulting file is a single,
portable, consistent snapshot.

### Pre-migration backups (automatic)

The lifespan handler writes an automatic backup to
`data/migration_backups/migration_<ISO-timestamp>.db` **before** it
applies any pending alembic migration. These are the fallback if a
migration fails — they are not a substitute for routine backups.

```bash
ls -lh data/migration_backups/
# migration_2026-04-22T12_16_40.db
```

Rotation is not automatic. Operators are responsible for pruning old
migration backups once a release is known-good — the directory is
otherwise append-only.

### Restore

To restore the **runtime database** from a routine backup:

```bash
# Stop the service first — restoring into a live aiosqlite connection
# produces a corrupt database.
pkill -TERM -f "stoat_ferret.api"

# Replace data/stoat.db (and delete the WAL/SHM sidecars so SQLite does
# not attempt to replay stale WAL against the restored file).
cp data/backups/stoat_20260424T090000Z.db data/stoat.db
rm -f data/stoat.db-wal data/stoat.db-shm

# Restart; the startup migration pass will no-op if the schema is
# already current.
uv run python -m stoat_ferret.api
```

Verify the restore:

```bash
curl -s http://localhost:8765/health/ready | python -c "import json,sys;d=json.load(sys.stdin);print(d['checks']['database'])"
# {'status': 'ok', 'latency_ms': 0.47, 'version': '3.50.4'}

curl -s http://localhost:8765/api/v1/version | python -m json.tool
```

`database_version` in the `/api/v1/version` response must match the
alembic revision of the source database.

### Migrations (manual)

Migrations run automatically on startup, but operators can apply them
manually when verifying a schema change before deploy:

```bash
# Apply any pending migrations.
uv run alembic upgrade head

# Current revision.
uv run alembic current

# Revision history.
uv run alembic history
```

`alembic.ini` uses `sqlalchemy.url=sqlite:///stoat_ferret.db` for the
Alembic CLI path — not the application's `STOAT_DATABASE_PATH`. To
target the runtime database explicitly:

```bash
uv run alembic -x sqlalchemy.url=sqlite:///data/stoat.db upgrade head
```

### Fixture Reset

Use this procedure to discard the current runtime database and restart from
the seed fixture baseline. This is a destructive operation for the runtime
database — all user data in `data/stoat.db` will be lost.

**When to use:** Development environment database is corrupt, schema is
inconsistent, or you want a clean slate matching the seed data.

**Steps:**

1. Stop the service:
   ```bash
   pkill -TERM -f "stoat_ferret.api"
   ```

2. Delete the runtime database and WAL/SHM sidecars:
   ```bash
   rm -f data/stoat.db data/stoat.db-wal data/stoat.db-shm
   ```

3. Start the service. On startup, the server detects that `data/stoat.db`
   is absent and automatically copies `tests/fixtures/stoat.seed.db` to
   `data/stoat.db`, then runs Alembic migrations to reach the current
   schema head:
   ```bash
   uv run python -m stoat_ferret.api
   ```

4. Verify the reset:
   ```bash
   curl -s http://localhost:8765/health/ready | python -c "import json,sys;d=json.load(sys.stdin);print(d['checks']['database'])"
   # {'status': 'ok', 'latency_ms': 0.47, 'version': '3.50.4'}
   ```

**Fixture path:** The immutable seed fixture is `tests/fixtures/stoat.seed.db`
— it is tracked in git and never modified at runtime. See
[`docs/setup/02_development-setup.md`](../setup/02_development-setup.md#initialize-the-database)
for the fixture-vs-runtime model explanation.

---

## Log locations and rotation

The logger writes **stdout** and a **rotating file** with identical
JSON-structured payloads.

| Path | Format | Rotation |
|------|--------|----------|
| stdout | structlog JSON (or console in dev) | uvicorn / container log pipeline |
| `logs/stoat-ferret.log` | structlog JSON | `STOAT_LOG_MAX_BYTES` (default 10485760) / `STOAT_LOG_BACKUP_COUNT` (default 5) |

Rotation produces `logs/stoat-ferret.log.1` through
`logs/stoat-ferret.log.5` by default. Setting `STOAT_LOG_MAX_BYTES=0`
disables rotation; setting `STOAT_LOG_BACKUP_COUNT=0` keeps only the
current file. See
[`docs/setup/04_configuration.md#logging`](../setup/04_configuration.md#logging).

### Key event names to grep

| Event | Meaning |
|-------|---------|
| `deployment.startup` | Final startup log line — includes `app_version`, `core_version`, `git_sha` (runtime-resolved, same as `app_sha` in `/api/v1/version`), `sqlite_version`. Its absence after boot indicates startup never completed. |
| `deployment.migration.*` | Migration result: `already_current`, `success`, `failed`, `unexpected_error`. |
| `deployment.feature_flag` | One line per `STOAT_*` flag at startup — your audit record for what toggles were active. |
| `render_shutdown.*` | Shutdown-path render teardown. `killed_remaining` (warning) means FFmpeg did not exit during the grace window. |
| `render_checkpoint.recovery` | Non-zero `interrupted_jobs` means the previous process died mid-render and the jobs were re-queued. |
| `system_state.*_unavailable` | The `/api/v1/system/state` snapshot could not reach a subsystem (graceful partial state). |
| `version.requested` | Every call to `/api/v1/version`. |

Follow the live file:

```bash
tail -f logs/stoat-ferret.log
```

Grep structured events (jq makes the output readable):

```bash
grep '"event": "deployment.startup"' logs/stoat-ferret.log | tail -1 | jq .
```

---

## Performance tuning

Full reference: [`docs/setup/04_configuration.md`](../setup/04_configuration.md)
— do not duplicate env-var tables here.

Three knobs account for the majority of deployment-time tuning:

| Env var | Default | Field type | When to adjust |
|---------|---------|------------|----------------|
| [`STOAT_WS_REPLAY_BUFFER_SIZE`](../setup/04_configuration.md#websocket) | 1000 | int | Raise if reconnecting WebSocket clients report missed events — especially under bursty render activity. Memory is O(buffer size) globally, not per-client. |
| [`STOAT_RENDER_MAX_CONCURRENT`](../setup/04_configuration.md#render) | 4 (range 1–16) | int | Raise when CPU is underused and queue depth stays elevated; lower when `render.disk_usage_percent` trends above `STOAT_RENDER_DISK_DEGRADED_THRESHOLD` (default 0.9). |
| [`STOAT_RENDER_TIMEOUT_SECONDS`](../setup/04_configuration.md#render) | 3600 (range 60–86400) | int | Raise for long-form output (hour-plus timeline); lower when renders should fail-fast and be retried. |

Tuning procedure:

1. Start from defaults. They are chosen to avoid resource exhaustion
   on a 4-core / 8 GB host with an SSD.
2. Observe `/metrics` and `/api/v1/render/queue` under representative
   load for at least 15 minutes.
3. Change **one** knob at a time, restart the service (settings are
   cached via `@lru_cache` on `get_settings()` — see
   `src/stoat_ferret/api/settings.py`), and observe for another soak
   window.
4. Link the resulting values into your deployment manifest / Docker
   compose file so the tuning is reproducible.

All settings are pinned to the `STOAT_` prefix and verified against the
source of truth: `src/stoat_ferret/api/settings.py`.

---

## Container deployment checklist

The production `Dockerfile` is a two-stage build (`builder` compiles
the Rust extension and frontend assets, `runtime` is a `python:3.10-slim`
image). Key build invariants are enforced at the Dockerfile level:

- `maturin build` runs at the project root (not from a `rust/`
  subdirectory) — see the [build-tooling guidance in AGENTS.md](../../AGENTS.md#type-stubs).
- The runtime image installs the pre-built wheel via `uv pip install`
  so `hatchling` is never asked to produce the Rust extension.
- `curl` is present in the runtime image so `HEALTHCHECK CMD` can hit
  `/health/live`.

### Pre-flight

```bash
# 1. Build the image.
docker build -t stoat-ferret:latest .

# 2. Run with explicit database and proxy paths (containers should
#    always mount these to persistent volumes).
docker run -d --name stoat-ferret \
  -p 8765:8765 \
  -v "$PWD/data:/app/data" \
  -v "$PWD/logs:/app/logs" \
  -e STOAT_API_HOST=0.0.0.0 \
  -e STOAT_DATABASE_PATH=/app/data/stoat.db \
  -e STOAT_ALLOWED_SCAN_ROOTS='["/app/videos"]' \
  stoat-ferret:latest

# 3. Verify liveness (the smoke script mirrors the container HEALTHCHECK).
STOAT_HOST=localhost STOAT_PORT=8765 bash scripts/deploy_smoke.sh
```

### Environment variables (mandatory audit)

Before promoting an image, confirm each of these is set to a value
reviewed by the deploy reviewer. All names use the `STOAT_` prefix
(case insensitive; `STOAT_API_PORT` and `stoat_api_port` are treated
identically).

- `STOAT_API_HOST` — `0.0.0.0` inside containers, otherwise `127.0.0.1`.
- `STOAT_API_PORT` — match the published port.
- `STOAT_DATABASE_PATH` — a path on a persistent volume.
- `STOAT_THUMBNAIL_DIR`, `STOAT_PROXY_OUTPUT_DIR`,
  `STOAT_PREVIEW_OUTPUT_DIR`, `STOAT_RENDER_OUTPUT_DIR`,
  `STOAT_WAVEFORM_DIR`, `STOAT_MIGRATION_BACKUP_DIR` — all on the
  persistent volume; the server will `mkdir -p` as needed but does not
  survive volume loss.
- `STOAT_ALLOWED_SCAN_ROOTS` — JSON array of allowed scan paths;
  leaving this unset (empty list) allows every directory the process
  can read. For untrusted operators, set it.
- `STOAT_WS_REPLAY_BUFFER_SIZE`, `STOAT_RENDER_MAX_CONCURRENT`,
  `STOAT_RENDER_TIMEOUT_SECONDS` — tune per host capacity (see
  [Performance tuning](#performance-tuning)).

### Render worker caveat

> **Important.** The HTTP server accepts render submissions and exposes
> full status/cancel/retry endpoints, but **a bare
> `python -m stoat_ferret.api` process does not dequeue and execute
> render jobs**. In the current deployment topology, render jobs
> remain in `queued` until `RenderService.run_job(job, command)` is
> driven by an external caller (tests, a future dedicated worker
> service). See the
> [stuck render jobs troubleshooting tree](troubleshooting.md#tree-2-stuck-render-jobs).
>
> Batch renders (`POST /api/v1/render/batch`) similarly require
> `app.state.batch_render_handler` to be wired at deploy time — the
> default is `None`, which causes batch jobs to transition
> `pending → running → completed` instantly without invoking FFmpeg.

### Post-deploy verification

```bash
bash scripts/deploy_smoke.sh
curl -s http://localhost:8765/api/v1/version | python -m json.tool
curl -sL http://localhost:8765/metrics | head -5
```

`/api/v1/version` reports `app_version`, `core_version`,
`git_sha` (Rust compile-time SHA), `app_sha` (runtime-resolved SHA),
`python_version`, and `database_version` (the alembic revision currently
applied). Use `app_sha` to verify you are testing the current Python HEAD
after a Python-only release — `git_sha` reflects the Rust compile time and
may lag behind by multiple Python-only releases. A mismatch between `app_sha`
and the expected commit is a reliable signal that the wrong build is deployed.

---

## Monitoring

### Health endpoints

| Endpoint | Intended consumer | Timeout budget | Blocks on |
|----------|-------------------|----------------|-----------|
| `GET /health/live` | k8s liveness, load-balancer ping | <10 ms | Nothing — always 200 if uvicorn is responsive |
| `GET /health/ready` | k8s readiness, traffic shaping | <100 ms typical | Runs each subsystem check with a 5 s per-check timeout |
| `GET /api/v1/system/state` | Ops dashboards, synthetic monitors | <300 ms typical | In-memory job queue + WS manager scan; no DB I/O |
| `GET /api/v1/version` | Deploy verification | <50 ms | Single indexed SQLite row for alembic revision |
| `GET /metrics` | Prometheus | varies | In-process counter/gauge snapshot |

### Prometheus metrics

The `/metrics` endpoint is mounted at `/metrics` via the official
`prometheus_client.make_asgi_app()`. FastAPI's redirect-slashes
behavior returns a 307 from `/metrics` to `/metrics/`, so scrapers
must follow redirects (Prometheus does by default; `curl -L` when
hand-testing).

```bash
curl -sL http://localhost:8765/metrics | head
```

Key metric families exposed today:

| Metric | Type | Use |
|--------|------|-----|
| `http_requests_total{method,path,status}` | counter | Per-endpoint throughput and error rate |
| `http_request_duration_seconds{method,path}` | histogram | Endpoint latency distribution |
| `stoat_ferret_ffmpeg_executions_total` | counter | Render throughput at the FFmpeg boundary |
| `stoat_ferret_ffmpeg_execution_duration_seconds` | histogram | Render-duration distribution |
| `stoat_ferret_ffmpeg_active_processes` | gauge | Live FFmpeg child count — alert on sustained high values |
| `stoat_ferret_effect_applications_total{effect_type}` | counter | Effect usage by type |
| `stoat_ferret_transition_applications_total{transition_type}` | counter | Transition usage by type |
| `video_editor_preview_sessions_active` | gauge | Current preview sessions |
| `video_editor_preview_cache_hit_ratio` | gauge | Preview cache hit ratio (0.0–1.0) |
| `video_editor_proxy_files_total{status}` | gauge | Proxy pipeline pipeline health |
| `video_editor_proxy_storage_bytes` | gauge | Toward `STOAT_PROXY_MAX_STORAGE_BYTES` |
| `synthetic_check_total{probe,result}` | counter | Synthetic monitoring outcomes (when enabled) |

### Key signals to watch

| Signal | Source | Alarm when |
|--------|--------|------------|
| Readiness regression | `/health/ready` `status=="degraded"` with HTTP 503 | >1 minute sustained |
| Queue backpressure | `/api/v1/render/queue` `pending_count` vs. `max_queue_depth` | `pending_count / max_queue_depth > 0.8` for >5 min |
| Disk pressure | `/api/v1/render/queue` `disk_available_bytes` | `<10%` of `disk_total_bytes` |
| Job worker stopped | `logs/stoat-ferret.log` — missing `worker_started` after start | any occurrence |
| WS memory pressure | `ws_buffer_utilization` in `/health/ready` | sustained high value relative to `STOAT_WS_REPLAY_BUFFER_SIZE` |
| Render stuck queued | `/api/v1/render?status=queued` | a job older than 5 min with `active_count==0` (see the [troubleshooting tree](troubleshooting.md#tree-2-stuck-render-jobs)) |

`/api/v1/system/state` returns the same snapshot that bootstraps
WebSocket subscribers — dashboards can reuse a single query rather
than polling every status endpoint.

---

## Related documentation

- [`docs/setup/04_configuration.md`](../setup/04_configuration.md) —
  env-var reference and defaults.
- [`docs/setup/05_troubleshooting.md`](../setup/05_troubleshooting.md) —
  installation, build, and toolchain troubleshooting.
- [`docs/manual/troubleshooting.md`](troubleshooting.md) — runtime
  failure decision trees (health, render, WebSocket, latency).
- [`docs/manual/api-usage-examples.md`](api-usage-examples.md) — live-validated
  API workflows keyed off the same endpoints documented here.
- [`docs/design/VALIDATION_FRAMEWORK.md`](../design/VALIDATION_FRAMEWORK.md) —
  the evidence pattern used to verify every command in this runbook.
- `src/stoat_ferret/api/settings.py` — the authoritative source for
  env-var names, defaults, and validation ranges.
