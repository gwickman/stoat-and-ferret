# Health Check Router

**Source:** `src/stoat_ferret/api/routers/health.py`
**Component:** API Gateway

## Purpose

Provides liveness and readiness probe endpoints for container orchestration (Kubernetes, Docker). Liveness indicates server is running; readiness checks dependencies (database, FFmpeg).

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health/live | Liveness probe - always returns 200 if server responds |
| GET | /health/ready | Readiness probe - returns 200 if all dependencies healthy, 503 if any check fails |

### Functions

- `liveness() -> dict[str, str]`: Returns `{"status": "ok"}`

- `readiness(request: Request) -> JSONResponse`: Returns JSON with status and individual check results. Returns 200 if all checks pass, 503 if degraded.

- `_check_database(request: Request) -> dict[str, Any]`: Checks database connectivity by executing `SELECT 1`. Returns dict with status and latency_ms on success, or status and error on failure.

- `_check_ffmpeg() -> dict[str, Any]`: Checks FFmpeg availability by running `ffmpeg -version` in executor. Parses version from output. Returns dict with status and version on success, or status and error on failure.

## Key Implementation Details

- **Liveness**: Minimal check with no dependency verification; meant to be called frequently (typically every 5-10 seconds)
- **Readiness**: Comprehensive check of database and FFmpeg; suitable for less frequent calls (typically every 30 seconds)
- **Graceful degradation**: Readiness returns 503 SERVICE_UNAVAILABLE if any check fails, with per-check status for debugging
- **Async execution**: Database check uses async await; FFmpeg check runs synchronously in executor via `asyncio.to_thread()`
- **Timeout**: FFmpeg check has 5-second subprocess timeout to prevent hanging
- **Database connection handling**: Checks if db exists on app.state; if None (test mode), assumes OK and returns 0ms latency

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `fastapi`: Router, APIRouter, Request, status
- `shutil.which`: Locate ffmpeg in PATH
- `subprocess.run`: Execute ffmpeg command
- `asyncio.to_thread`: Run sync subprocess in executor

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Accessed by**: Container orchestration platforms, load balancers
