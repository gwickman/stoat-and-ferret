# Health Check Router

**Source:** `src/stoat_ferret/api/routers/health.py`
**Component:** API Gateway

## Purpose

Provides liveness and readiness probe endpoints for container orchestration (Kubernetes, Docker). Liveness indicates server is running; readiness checks critical dependencies (database, FFmpeg) and non-critical subsystems (preview, proxy, render) using the degraded-but-healthy pattern (LRN-136).

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health/live | Liveness probe - always returns 200 if server responds |
| GET | /health/ready | Readiness probe - returns 200 (ok or degraded) if critical checks pass, 503 only on critical failure |

### Functions

- `liveness() -> dict[str, str]`: Returns `{"status": "ok"}`

- `readiness(request: Request) -> JSONResponse`: Returns JSON with status and individual check results. Critical failures (database, FFmpeg) return 503. Non-critical degradation (preview, proxy, render) returns 200 with `"status": "degraded"`.

- `_check_database(request: Request) -> dict[str, Any]`: Checks database connectivity by executing `SELECT 1`. Returns dict with status and latency_ms on success, or status and error on failure.

- `_check_ffmpeg() -> dict[str, Any]`: Checks FFmpeg availability by running `ffmpeg -version` in executor. Parses version from output. Returns dict with status and version on success, or status and error on failure.

- `_check_preview(request: Request) -> dict[str, Any]`: Checks preview subsystem. Returns active_sessions and cache_usage_percent. Status is "degraded" if cache usage > 90%.

- `_check_proxy(request: Request) -> dict[str, Any]`: Checks proxy subsystem. Returns proxy_dir_writable and pending_proxies. Status is "degraded" if directory not writable or excessive pending proxies.

- `_check_render(request: Request) -> dict[str, Any]`: Checks render subsystem. Returns active_jobs, queue_depth, disk_usage_percent, encoder_available. Status is "degraded" if disk_usage_percent exceeds `render_disk_degraded_threshold` or queue_depth/max_depth > 0.8. Status is "unavailable" if FFmpeg not found via `shutil.which("ffmpeg")`.

### Readiness Response Schema

```json
{
  "status": "ok" | "degraded",
  "checks": {
    "database": {"status": "ok" | "error", "latency_ms": float},
    "ffmpeg": {"status": "ok" | "error", "version": str},
    "preview": {"status": "ok" | "degraded" | "error", "active_sessions": int, "cache_usage_percent": float},
    "proxy": {"status": "ok" | "degraded", "proxy_dir_writable": bool, "pending_proxies": int},
    "render": {"status": "ok" | "degraded" | "unavailable", "active_jobs": int, "queue_depth": int, "disk_usage_percent": float, "encoder_available": bool}
  }
}
```

## Key Implementation Details

- **Liveness**: Minimal check with no dependency verification; meant to be called frequently (typically every 5-10 seconds)
- **Readiness**: Checks critical dependencies (database, FFmpeg) and non-critical subsystems (preview, proxy, render)
- **Degraded-but-healthy pattern (LRN-136)**: Non-critical subsystem issues return HTTP 200 with `"status": "degraded"` instead of HTTP 503. Only critical failures (database, FFmpeg) cause 503. This prevents unnecessary restarts when non-essential subsystems are overloaded.
- **Async execution**: Database check uses async await; FFmpeg check runs synchronously in executor via `asyncio.to_thread()`
- **Timeout**: FFmpeg check has 5-second subprocess timeout to prevent hanging
- **Database connection handling**: Checks if db exists on app.state; if None (test mode), assumes OK and returns 0ms latency
- **Render disk threshold**: Configurable via `render_disk_degraded_threshold` setting

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.settings.Settings`: Configuration for thresholds
- `stoat_ferret.render.queue.RenderQueue`: Queue depth and active count queries
- `stoat_ferret.render.metrics.render_disk_usage_bytes`: Disk usage metric

### External Dependencies

- `fastapi`: Router, APIRouter, Request, status
- `shutil.which`: Locate ffmpeg in PATH
- `subprocess.run`: Execute ffmpeg command
- `asyncio.to_thread`: Run sync subprocess in executor

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Accessed by**: Container orchestration platforms, load balancers, Web GUI health dashboard
- **Checks**: Database, FFmpeg, Preview subsystem, Proxy subsystem, Render subsystem
