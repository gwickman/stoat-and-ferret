# Handoff: 003-health-endpoints

## What Was Done

Added health check endpoints:
- `GET /health/live` - Simple liveness probe (always returns 200)
- `GET /health/ready` - Readiness probe with database and FFmpeg checks

## API Structure

The health router is mounted at `/health`:
- Router defined in `src/stoat_ferret/api/routers/health.py`
- Registered in `src/stoat_ferret/api/app.py`

## Response Formats

### Liveness
```json
{"status": "ok"}
```

### Readiness (healthy)
```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "latency_ms": 1.2},
    "ffmpeg": {"status": "ok", "version": "6.0"}
  }
}
```

### Readiness (degraded)
Returns HTTP 503 with:
```json
{
  "status": "degraded",
  "checks": {
    "database": {"status": "error", "error": "..."},
    "ffmpeg": {"status": "ok", "version": "6.0"}
  }
}
```

## For Next Features

- The health router pattern can be followed for other routers (e.g., projects, timeline, etc.)
- The `request.app.state.db` pattern is used to access the database connection
- Additional health checks can be added to the readiness endpoint as needed
