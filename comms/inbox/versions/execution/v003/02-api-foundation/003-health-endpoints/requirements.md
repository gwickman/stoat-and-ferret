# Health Endpoints

## Goal
Create health check endpoints for liveness and readiness probes.

## Requirements

### FR-001: Liveness Endpoint
`GET /health/live` returns:
```json
{"status": "ok"}
```
- Always returns 200 if server is running
- No dependency checks

### FR-002: Readiness Endpoint
`GET /health/ready` returns:
```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok", "latency_ms": 1.2},
    "ffmpeg": {"status": "ok", "version": "6.0"}
  }
}
```
- Returns 200 if all checks pass
- Returns 503 if any check fails

### FR-003: Database Check
Verify database connection by executing simple query.

### FR-004: FFmpeg Check
Verify ffmpeg available by running `ffmpeg -version`.

## Acceptance Criteria
- [ ] `/health/live` returns 200
- [ ] `/health/ready` returns 200 when healthy
- [ ] `/health/ready` returns 503 when database unavailable
- [ ] `/health/ready` returns 503 when ffmpeg unavailable