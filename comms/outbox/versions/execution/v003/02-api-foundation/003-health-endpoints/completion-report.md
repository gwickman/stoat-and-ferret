---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 003-health-endpoints

## Summary

Implemented health check endpoints for liveness and readiness probes as specified in the requirements.

## Implementation

### Files Created
- `src/stoat_ferret/api/routers/health.py` - Health router with `/health/live` and `/health/ready` endpoints
- `tests/test_api/test_health.py` - Comprehensive tests for health endpoints

### Files Modified
- `src/stoat_ferret/api/app.py` - Registered health router

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `/health/live` returns 200 | PASS |
| `/health/ready` returns 200 when healthy | PASS |
| `/health/ready` returns 503 when database unavailable | PASS |
| `/health/ready` returns 503 when ffmpeg unavailable | PASS |

## Test Coverage

6 new tests added covering:
- Liveness endpoint always returns 200 with `{"status": "ok"}`
- Readiness returns 200 when all checks pass
- Readiness returns 503 when database unavailable
- Readiness returns 503 when ffmpeg not found
- Readiness returns 503 when ffmpeg command fails
- Readiness response structure validation

## Technical Notes

- Database check uses `SELECT 1` query and measures latency
- FFmpeg check uses `shutil.which()` to find the binary and `ffmpeg -version` to verify it works
- Both checks report errors with descriptive messages when they fail
- Response includes individual check statuses to aid debugging
