# FFmpeg Observability

## Goal
Add structured logging and Prometheus metrics to FFmpeg execution.

## Requirements

### FR-001: Structured Logging
- Log every FFmpeg command with:
  - correlation_id (from context or generated)
  - command args (truncated for safety)
  - duration
  - return code
  - success/failure status

### FR-002: Prometheus Metrics
Create metrics:
- ffmpeg_executions_total (Counter, labels: status=success|failure)
- ffmpeg_execution_duration_seconds (Histogram)
- ffmpeg_active_processes (Gauge)

### FR-003: ObservableFFmpegExecutor
- Wrapper that adds logging/metrics to any executor
- Accepts optional correlation_id parameter

### FR-004: Add Dependencies
- structlog>=24.0
- prometheus-client>=0.20

## Acceptance Criteria
- [ ] Structured logs emitted for every execution
- [ ] Prometheus metrics incremented correctly
- [ ] Metrics include duration histogram
- [ ] Can wrap any executor implementation

## Evidence
- prometheus-client specified: `docs/design/07-quality-architecture.md`