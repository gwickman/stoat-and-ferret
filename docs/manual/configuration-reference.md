# Configuration Reference (Operator / Security)

Security-focused operator guide for the `STOAT_*` environment variables that affect deployment surface area, data retention, and resource ceilings. Use this document when hardening a deployment, reviewing a change request, or responding to a configuration-related incident.

This guide covers the 13 variables that previously carried a documentation drift finding (P2-CONFIG-001 in `docs/security/review-phase6.md`); each entry calls out the operational behaviour and the security-relevant implications. Variable name, type, default, and valid range mirror the canonical reference in [`docs/setup/04_configuration.md`](../setup/04_configuration.md) — no description here contradicts the setup doc.

## Scope and Process Anchor

- **Scope:** Production deployments, staging environments, and any deployment exposed beyond a developer workstation.
- **Authority:** The Pydantic `Settings` model in `src/stoat_ferret/api/settings.py` is the single source of truth for variable names, types, defaults, and validation ranges. This document explains the **operational and security** consequences of those settings; it does not redefine them.
- **Process rule:** When a new `STOAT_*` variable is added to `Settings`, both this file and `docs/setup/04_configuration.md` must be updated in the same backlog item, and the audit drift baseline (`KNOWN_UNDOCUMENTED_SETTINGS_VARS` in `tests/security/test_audit.py`) must remain empty. The authoritative process rule lives in [`AGENTS.md` § Documentation Standards](../../AGENTS.md#documentation-standards) — refer to that section rather than restating the rule here.

## Batch Rendering

Batch rendering exposes the `/api/v1/batch/*` routes that accept multi-job render requests. Disabling batch rendering removes the routes entirely; misconfigured limits expose CPU and FFmpeg process pressure.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_BATCH_RENDERING` | `bool` | `true` | Enable batch rendering support. When `false`, the `/api/v1/batch/*` routes return 404 and batch jobs cannot be submitted. Disable in deployments that should accept only single-job render submissions. |
| `STOAT_BATCH_MAX_JOBS` | `int` | `20` | Maximum number of jobs allowed in a single batch request (valid range: 1-100). Requests exceeding this limit are rejected with a validation error. |

**Security implications**

- `STOAT_BATCH_MAX_JOBS` is a denial-of-service guard: the limit caps the work a single client can queue in one request. Raising it on an internet-exposed deployment increases the cost of a hostile or malformed batch submission. Keep at the default unless you have an inbound rate-limit or authentication layer that bounds caller concurrency.
- Disabling `STOAT_BATCH_RENDERING` is a coarse mitigation — operators responding to a batch-route incident can set it to `false` to take all batch endpoints offline without redeploying code.

## Render Worker

The render worker loop dequeues jobs from the render queue and drives them through the render pipeline as a background asyncio task.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STOAT_RENDER_WORKER_ENABLED` | `bool` | `true` | Enable the background render worker loop. When `false`, jobs accumulate in the queue but are never dequeued; useful for UAT environments that assert on queue state without a running worker. |

**Security implications**

- Disabling `STOAT_RENDER_WORKER_ENABLED` is intended for test and UAT environments only. In production, leaving it `false` causes submitted render jobs to queue indefinitely without being processed.

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

## See Also

- [Setup — Configuration Reference](../setup/04_configuration.md) — full canonical reference for all 41 `STOAT_*` variables (name, type, default, valid range, plain-language description). Use this document for security-focused guidance and that document for the comprehensive list.
- [Operator Runbook](runbook.md) — start, stop, back up, and monitor the service.
- [Troubleshooting](troubleshooting.md) — decision trees for runtime incidents.
- [Security Review (Phase 6)](../security/review-phase6.md) — original audit findings and the drift-baseline probe details.
- [`AGENTS.md` § Documentation Standards](../../AGENTS.md#documentation-standards) — authoritative process rule for adding new `STOAT_*` variables.
