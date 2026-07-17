# Configuration Reference (Operator / Security)

Security-focused operator guide for the `STOAT_*` environment variables that affect deployment surface area, data retention, and resource ceilings. Use this document when hardening a deployment, reviewing a change request, or responding to a configuration-related incident.

This guide covers the 13 variables that previously carried a documentation drift finding (P2-CONFIG-001 in `docs/security/review-phase6.md`); each entry calls out the operational behaviour and the security-relevant implications. Variable name, type, default, and valid range mirror the canonical reference in [`docs/setup/04_configuration.md`](../setup/04_configuration.md) — no description here contradicts the setup doc.

## Scope and Process Anchor

- **Scope:** Production deployments, staging environments, and any deployment exposed beyond a developer workstation.
- **Authority:** The Pydantic `Settings` model in `src/stoat_ferret/api/settings.py` is the single source of truth for variable names, types, defaults, and validation ranges. This document explains the **operational and security** consequences of those settings; it does not redefine them.
- **Process rule:** When a new `STOAT_*` variable is added to `Settings`, both this file and `docs/setup/04_configuration.md` must be updated in the same backlog item, and the audit drift baseline (`KNOWN_UNDOCUMENTED_SETTINGS_VARS` in `tests/security/test_audit.py`) must remain empty. The authoritative process rule lives in [`AGENTS.md` § Documentation Standards](../../AGENTS.md#documentation-standards) — refer to that section rather than restating the rule here.

## Asset Library

The asset library (`/api/v1/assets`) stores user-uploaded files (PNG and JPEG in v090) by content hash and returns stable UUIDs for cross-project reference. Two settings govern storage location and upload size.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_ASSETS_DIR` | `Path` | `working/assets` | Directory for storing uploaded user asset files. Created automatically if it does not exist. Relative paths are resolved from the working directory. Files are stored under content-hash-derived names (`<sha256hex>.<ext>`) for deduplication. |
| `STOAT_ASSETS_MAX_SIZE_BYTES` | `int` | `104857600` | Maximum upload size in bytes for `POST /api/v1/assets` (default 100 MB). Uploads exceeding this limit are rejected with HTTP 413 before any disk write. Valid range: 1 to any positive integer. |

**Security implications**

- `STOAT_ASSETS_DIR` must be accessible to the server process and should reside **outside** the project repository root. Placing it inside the repo root risks committing uploaded binary files if `git add -A` is run without a well-configured `.gitignore`. For production, use a path on a dedicated data volume.
- All filesystem operations resolve the destination path under `STOAT_ASSETS_DIR` using `Path.resolve()` and verify the result starts with the resolved root before any write. Path traversal attempts (`../`, absolute paths, symlink chains) are rejected with HTTP 422 at the service layer — the check runs before any I/O.
- `STOAT_ASSETS_MAX_SIZE_BYTES` is the primary denial-of-service guard for the upload endpoint. An internet-facing deployment without authentication should keep this at the default or lower. Raising it on an unauthenticated API increases the potential for disk-exhaustion attacks via repeated large uploads.
- File type validation uses Pillow `Image.open()` magic-bytes sniffing rather than the caller-supplied MIME extension. A renamed TIFF or HEIC file is rejected (HTTP 415) even if the extension says `.png`. This prevents storing files that downstream FFmpeg builds may not support.

## Filesystem Scan Scope

`GET /api/v1/filesystem/directories` and `POST /api/v1/videos/scan` resolve a caller-supplied
directory path. The two variables below jointly determine whether an empty allowlist means
"allow all" (safe on a developer workstation) or "fail closed" (required once the server is
reachable over the network).

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_ALLOWED_SCAN_ROOTS` | `list[str]` | `[]` (empty) | Allowed root directories for scanning. See exposure-conditional behaviour below. |
| `STOAT_API_HOST` | `str` | `127.0.0.1` | Host the API server binds to. Loopback values (`127.0.0.1`, `::1`, `localhost`, case-insensitive) are the trust boundary for the check below. |

**Security implications**

- **Exposure-conditional fail-closed (BL-637).** When `STOAT_ALLOWED_SCAN_ROOTS` is empty AND
  `STOAT_API_HOST` is a loopback value, both endpoints keep the historical allow-all behaviour —
  this preserves local/dev/test/UAT usage unchanged on every platform and checkout location. When
  `STOAT_ALLOWED_SCAN_ROOTS` is empty AND `STOAT_API_HOST` is **not** loopback (e.g. `0.0.0.0`, the
  Dockerfile's shipped default), both endpoints return HTTP 403 instead of enumerating the
  filesystem. **No silent default root (e.g. `$HOME`) is ever substituted** — the operator must set
  an explicit allowlist to unblock a network-exposed deployment.
- **Why not a location-based default:** a default root would break test/CI/container checkouts
  whose paths sit outside it (pytest `tmp_path` is outside `$HOME` on Linux/macOS; the container
  runs at `/app`, outside `$HOME=/root`). Tying the control to bind exposure instead of location
  keeps all local usage working while closing the gap exactly where it exists — on an
  unauthenticated, network-reachable deployment.
- **Shipped container default:** `docker-compose.yml` sets `STOAT_ALLOWED_SCAN_ROOTS` to the
  mounted data volume (`/app/data`) so the shipped `0.0.0.0` bind (`Dockerfile`) does not
  immediately fail closed out of the box. Operators changing the data mount path must update this
  variable to match, or scanning will return 403.
- **Malformed paths return 400, not 500.** A null-byte or otherwise malformed `path` is rejected
  with a structured HTTP 400 rather than propagating an unhandled `ValueError`/`OSError` from
  `Path.resolve()`.
- Once `STOAT_ALLOWED_SCAN_ROOTS` is non-empty, behaviour is unchanged from before this control:
  the allowlist is enforced regardless of bind address, and a path outside every configured root
  returns 403.

## Batch Rendering

Batch rendering exposes the `/api/v1/batch/*` routes that accept multi-job render requests. Disabling batch rendering removes the routes entirely; misconfigured limits expose CPU and FFmpeg process pressure.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_BATCH_RENDERING` | `bool` | `true` | Enable batch rendering support. When `false`, the `/api/v1/batch/*` routes return 404 and batch jobs cannot be submitted. Disable in deployments that should accept only single-job render submissions. |
| `STOAT_BATCH_MAX_JOBS` | `int` | `20` | Maximum number of jobs allowed in a single batch request (valid range: 1-100). Requests exceeding this limit are rejected with a validation error. |

**Security implications**

- `STOAT_BATCH_MAX_JOBS` is a denial-of-service guard: the limit caps the work a single client can queue in one request. Raising it on an internet-exposed deployment increases the cost of a hostile or malformed batch submission. Keep at the default unless you have an inbound rate-limit or authentication layer that bounds caller concurrency.
- Disabling `STOAT_BATCH_RENDERING` is a coarse mitigation — operators responding to a batch-route incident can set it to `false` to take all batch endpoints offline without redeploying code.

## Stale-Job Sweeper

The stale-job sweeper runs as a background asyncio task and recovers render jobs stuck in `status='running'` with no progress. It polls periodically and transitions each stale job to `status='failed'`, reducing MTTR from hours (executor timeout) to seconds (sweep interval + threshold).

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_RENDER_STUCK_THRESHOLD_SECONDS` | `int` | `300` | Age in seconds beyond which a running render job is considered stale and transitioned to `failed`. **Valid range: 60–3600 seconds.** Values outside this range cause server startup to fail with a pydantic `ValidationError` — the server will not start until the value is corrected. The default 300s is appropriate for noop mode. Production deployments using real render mode should increase to 1800s (30 min) to avoid premature failure of slow-but-progressing encodes. |

**Security implications**

- Setting this too low terminates legitimate renders prematurely, causing spurious `failed` events on the WebSocket bus and filling `error_message` with sweeper-termination text. For real-mode deployments with long-running encodes (high-resolution, multi-segment), keep at 1800s or higher.
- Setting this too high (near 3600s) reduces the MTTR benefit; stuck jobs hold worker slots blocked for longer. For noop-mode environments the default 300s is safe because noop renders complete in milliseconds.
- The sweeper emits `EventType.RENDER_FAILED` WebSocket events and `render.job_stale` structured log entries for each transition. Monitoring these events helps distinguish sweeper-triggered failures from genuine encode errors.

## Render Worker

The render worker loop dequeues jobs from the render queue and drives them through the render pipeline as a background asyncio task.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_RENDER_WORKER_ENABLED` | `bool` | `true` | Enable the background render worker loop. When `false`, jobs accumulate in the queue but are never dequeued; useful for UAT environments that assert on queue state without a running worker. |

**Security implications**

- Disabling `STOAT_RENDER_WORKER_ENABLED` is intended for test and UAT environments only. In production, leaving it `false` causes submitted render jobs to queue indefinitely without being processed.

## Render Evidence Access

The render evidence endpoint exposes FFmpeg execution details — command arguments, exit code, stderr tail, and output file path — for a completed render job. The endpoint is **disabled by default** because command arguments can contain API keys, bearer tokens, and STOAT_\* environment variable values that must not be visible to unauthenticated callers.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_RENDER_EVIDENCE_FULL_ACCESS` | `bool` | `false` | Enable the full render evidence endpoint (`GET /render/{job_id}/evidence`). When `false` (default), the endpoint returns 403. When `true`, it returns the FFmpeg command args, exit code, stderr tail, output path, and filter script path — with sensitive values redacted. |

**Security implications**

- Even with redaction in place (sk-or-v1-\* API keys and STOAT_\* env var values are replaced with `[REDACTED]`), enabling this endpoint exposes internal file paths, FFmpeg flags, and codec configuration to any caller who can reach the API. Enable only in trusted internal deployments or for operator-level debugging, and disable again after the debugging session.
- The redaction covers values that exactly match a current `STOAT_*` environment variable at request time. Values injected via non-STOAT env vars or config files are **not** automatically redacted — review the full command before exposing this endpoint externally.
- If a security incident involves a compromised render job or a leaked command argument, set this to `false` and restart the server to close the surface before investigating.

## Preview Cache

Preview generation produces HLS segment files cached on local disk and indexed in memory. The four preview variables collectively bound disk consumption, session lifetime, and concurrent session count. They directly limit the resources a client can consume by repeatedly opening preview sessions.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_PREVIEW_SESSION_TTL_SECONDS` | `int` | `3600` | Preview session time-to-live in seconds (minimum: 1). Sessions that exceed this TTL are eligible for expiry cleanup. Lower values shorten the window in which an abandoned session retains cached segments on disk. |
| `STOAT_PREVIEW_SEGMENT_DURATION` | `float` | `2.0` | HLS segment duration in seconds for preview generation (valid range: 1.0-6.0). Smaller values reduce playback startup latency at the cost of producing more segment files per session. |
| `STOAT_PREVIEW_CACHE_MAX_SESSIONS` | `int` | `5` | Maximum number of concurrent preview sessions retained in cache (valid range: 1-100). Oldest sessions are evicted when this limit is exceeded. |
| `STOAT_PREVIEW_CACHE_MAX_BYTES` | `int` | `1073741824` | Maximum total storage for the preview cache in bytes (default 1 GB, 0 = unlimited). When exceeded, least-recently-used preview sessions are evicted. **Setting `0` disables the size cap and removes the disk-usage upper bound.** |

**Security implications**

- The cache caps are the primary defence against preview-driven disk exhaustion. Setting `STOAT_PREVIEW_CACHE_MAX_BYTES=0` is intended for short-lived test rigs only — it disables the upper bound and lets an unbounded number of preview sessions fill the configured `STOAT_PREVIEW_OUTPUT_DIR`. Do not deploy with `0` in production.
- The TTL and the byte cap interact: a long TTL with a small byte cap evicts under disk pressure (LRU); a short TTL with a large byte cap evicts on age. For a multi-tenant or anonymous-access deployment, prefer aggressive TTL plus a generous byte cap so abandoned sessions clear quickly.
- Lower segment durations (close to `1.0`) increase the segment file count per session — noisy on disk and expensive to evict. Stay near the default unless the deployment requires very-low-latency HLS startup.

## Proxy Storage

Proxy generation produces reduced-resolution copies of source video used by the GUI for fast scrub. Two of the proxy variables in this set govern automatic enqueue behaviour and storage cleanup; the storage location and total cap are documented in `docs/setup/04_configuration.md`.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_PROXY_AUTO_GENERATE` | `bool` | `false` | When `true`, automatically queues proxy generation for newly scanned videos. Default is `false`; operators must explicitly enable to pre-generate proxies during ingest. |
| `STOAT_PROXY_CLEANUP_THRESHOLD` | `float` | `0.8` | Storage usage ratio (0.0-1.0) that triggers automatic proxy cleanup. When total proxy storage exceeds this fraction of `STOAT_PROXY_MAX_STORAGE_BYTES`, least-recently-accessed proxies are deleted. |

**Security implications**

- `STOAT_PROXY_AUTO_GENERATE=true` couples ingest cost to library-scan cost: every newly scanned video triggers an FFmpeg encode job. On deployments where the scan root is operator-controlled the risk is bounded; if any scan-trigger pathway is reachable by an external caller, leave at the default.
- The cleanup threshold is the failsafe that prevents proxy storage from saturating the volume hosting `STOAT_PROXY_OUTPUT_DIR`. Setting it too high (close to `1.0`) reduces the safety margin between "starting to clean up" and "disk full". Setting it too low triggers eviction more aggressively and can churn proxies that are still in active use. Stay near the default unless monitoring confirms a different operating point.

## Thumbnail Strips

Thumbnail strip sprite sheets are produced by extracting frames at fixed intervals across the source video. The interval governs the sprite file size and extraction time per video.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_THUMBNAIL_STRIP_INTERVAL` | `float` | `5.0` | Seconds between frames in thumbnail strip sprite sheets (minimum: 0.5). Smaller values produce denser strips at the cost of larger sprite files and longer extraction time. |

**Security implications**

- A very small interval (close to `0.5`) on a long source produces large sprite files. For deployments accepting operator-controlled uploads this is bounded; if scans run against externally supplied media, monitor `data/thumbnails/` size growth after lowering the interval.

## Testing and Synthetic Monitoring

> **Production hazard:** `STOAT_SEED_ENDPOINT` exposes the testing seed-data injection endpoint and must never be enabled in a production deployment. `STOAT_SYNTHETIC_MONITORING` opens an information-disclosure surface that is acceptable in trusted internal deployments but should be reviewed before being exposed externally.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_SEED_ENDPOINT` | `bool` | `false` | Enable the test seed endpoint (`POST /api/v1/testing/seed`). Requires `STOAT_TESTING_MODE=true`; the endpoint registers as 404 when either flag is unset. **Must never be set in production.** |
| `STOAT_SYNTHETIC_MONITORING` | `bool` | `false` | Enable synthetic monitoring probes that emit periodic health/metric events. Probes are observable on the `/metrics` endpoint and via WebSocket; consider the resulting information-disclosure surface before enabling on internet-facing deployments. |
| `STOAT_SYNTHETIC_MONITORING_INTERVAL_SECONDS` | `int` | `60` | Interval in seconds between synthetic monitoring probe cycles (minimum: 1). Lower values produce more frequent probes at the cost of additional load. |

**Security implications**

- `STOAT_SEED_ENDPOINT` is a layered guard with `STOAT_TESTING_MODE`: the seed endpoint is only registered when *both* are `true`. The defence-in-depth is intentional — do not invent a single-flag bypass. If a probe alerts on the seed endpoint being reachable in a production-tier environment, the response is to set both flags to `false` and rotate any credentials that may have been exposed during the window.
- Synthetic monitoring probes write event payloads that are observable on `/metrics` (Prometheus-format) and on the WebSocket event bus. The payload itself does not include user data, but the cadence (low interval) gives an outside observer a deterministic signal of server liveness. For deployments behind only a perimeter firewall, leave the default interval; for internet-exposed deployments, prefer a longer interval or disable until the metrics surface is gated.

## Version Retention

Project versions accumulate over time and grow the SQLite database. The retention setting bounds the per-project history that is retained across cleanup runs.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_VERSION_RETENTION_COUNT` | `int` (optional) | unset | Keep-last-N version retention per project (minimum: 1). When unset (the default), all versions are retained indefinitely. Older versions beyond the keep count are eligible for cleanup. |

**Security implications**

- Unset retention means project versions accumulate indefinitely. On a long-running deployment this grows the SQLite database without bound — a slow-rolling availability risk rather than a security exploit, but worth monitoring. Set a finite count for deployments where retention is a compliance or capacity concern; the limit applies per project and is enforced at cleanup time, not write time, so operators retain control over when truncation runs.

## Effect Limits

Some effects buffer large amounts of data in memory during processing. These settings let operators cap that memory pressure at the deployment level.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_REVERSE_MAX_DURATION_S` | `float` | `30.0` | Maximum clip duration in seconds allowed for the reverse effect (must be > 0). Clips exceeding this limit are rejected with HTTP 422 before the render job is queued. |

**Why this limit exists**

The FFmpeg `reverse` and `areverse` filters work by reading the entire clip segment into RAM before producing output — they cannot stream. A 30-second clip at typical bitrates consumes hundreds of megabytes. Without a cap, an operator or API caller can trigger a reverse on an arbitrarily long clip, exhausting server RAM and crashing the process.

**Tuning guidance**

- The default of 30 s is conservative and suitable for deployments with 4–8 GB of RAM per worker.
- Increase proportionally to available RAM and expected concurrent render load. A rough estimate: 1 minute of 1080p/30fps ProRes takes ~4–6 GB of buffered video frames.
- Values ≤ 0 are rejected at startup with a pydantic `ValidationError`.
- This limit applies per-clip. If multiple reverse-effect clips are rendered concurrently, peak RAM usage multiplies accordingly.

## TTS Narration

TTS narration synthesises speech audio from text cues placed on voice tracks. The feature supports a local Piper backend (default, no network required) and optional Kokoro cloud backends via OpenRouter.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_OPENROUTER_API_KEY` | `str \| None` | unset | OpenRouter API key for Kokoro TTS backends. Required when `STOAT_TTS_DEFAULT_BACKEND` is `openrouter_kokoro` or `openrouter_commercial`. Leave unset to use only the Piper local backend. |
| `STOAT_TTS_DEFAULT_BACKEND` | `str` | `piper_local` | Default TTS synthesis backend. One of: `piper_local` (GPL-3.0, local Piper subprocess), `openrouter_kokoro` (Apache 2.0, Kokoro via OpenRouter API), `openrouter_commercial` (commercial voice via OpenRouter). |
| `STOAT_TTS_PIPER_MODELS_DIR` | `str` | `data/piper_models` | Directory for Piper ONNX voice model files. Models are downloaded on first use; this directory must be writable by the server process. |
| `STOAT_TTS_CACHE_DIR` | `str` | `data/tts_cache` | Directory for caching synthesised audio files keyed by `sha256(text::voice::backend)`. **Changing this path orphans existing cached audio** — clear the old directory manually to reclaim disk space. |

**Security implications**

- `STOAT_OPENROUTER_API_KEY` is transmitted in the `Authorization: Bearer` header on every Kokoro API request. It is **not** redacted in application logs by default. Treat it as a secret credential — do not set it in a `.env` file committed to version control. Prefer setting it via the environment or a secrets manager.
- The Piper local backend (`piper_local`) invokes Piper as a subprocess using `subprocess.run`. The model path and voice arguments are derived from server-side configuration, not caller-supplied values, so the injection surface is bounded to operator-controlled paths.
- `STOAT_TTS_CACHE_DIR` caches synthesised audio keyed by content hash. Cached files are not access-controlled beyond filesystem permissions. On multi-tenant deployments, ensure the cache directory is not world-readable. Files are never deleted automatically — operators must manage cache growth.
- Kokoro 429 (rate-limited) and 400 (bad request) errors are surfaced as render-job errors with clear messages. There is **no silent fallback** to a different backend on API error — configure alerts on render failures if Kokoro availability is a concern.

## AGPL Compliance

The AGPL §13 source-offer affordance exposes source URL, version, and commit information via `GET /api/v1/source`. Operators serving modified instances over a network MUST set `STOAT_SOURCE_URL` to point at the corresponding source for the deployed commit.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_SOURCE_URL` | `str` | `https://github.com/gwickman/stoat-and-ferret` | URL of the corresponding source code for AGPL §13 compliance. Operators deploying modified instances MUST override to point at the actual deployed commit's source. |
| `STOAT_BUILD_COMMIT` | `str` | `"unknown"` | Build commit SHA injected by the deploy pipeline. Returned verbatim in `GET /api/v1/source`. If not set, returns `"unknown"`. |

**Security implications**

- `STOAT_SOURCE_URL` accepts any string — no URL-format validation is applied at the API layer. The GUI client accepts only absolute `http:`/`https:` URLs for this setting; any non-http(s), relative, or malformed value causes the StatusBar to display the default source link instead. An operator who sets this to a non-reachable URL satisfies the API contract but may not satisfy the AGPLv3 §13 legal obligation. Review the value during deployment hardening to ensure it points at a publicly accessible source archive.
- `STOAT_BUILD_COMMIT` is an informational field for operational traceability. It does not affect security posture. Omitting it (leaving `"unknown"`) reduces auditability but does not introduce a vulnerability.
- The `/api/v1/source` endpoint is unauthenticated by design — AGPL §13 requires that the source offer be available to all network-served users. Do not add authentication guards to this route.

## See Also

- [Setup — Configuration Reference](../setup/04_configuration.md) — full canonical reference for all `STOAT_*` variables (name, type, default, valid range, plain-language description). Use this document for security-focused guidance and that document for the comprehensive list.
- [Operator Runbook](runbook.md) — start, stop, back up, and monitor the service.
- [Troubleshooting](troubleshooting.md) — decision trees for runtime incidents.
- [Security Review (Phase 6)](../security/review-phase6.md) — original audit findings and the drift-baseline probe details.
- [`AGENTS.md` § Documentation Standards](../../AGENTS.md#documentation-standards) — authoritative process rule for adding new `STOAT_*` variables.
