# Phase 5: Observability & Operations

## Overview

Phase 5 introduces the render pipeline — long-running, resource-intensive FFmpeg processes that require comprehensive observability and operational controls. This document defines structured logging events, Prometheus metrics, health checks, resource management, and graceful degradation patterns for the render subsystem.

## Structured Logging Events

All events use structlog with correlation IDs per existing pattern. Events follow the convention: `{subsystem}_{action}_{result}`.

### Render Job Events

```python
# Job lifecycle
logger.info("render_job_created",
    job_id=job_id,
    project_id=project_id,
    output_format=output_format,
    quality_preset=quality_preset,
    encoder=encoder_name,
    hardware_accelerated=hw_accel,
    total_frames=total_frames,
    estimated_duration=estimated_duration,
)

logger.info("render_job_started",
    job_id=job_id,
    ffmpeg_command=command_str,
    encoder=encoder_name,
    two_pass=two_pass,
    output_path=output_path,
)

logger.info("render_progress",
    job_id=job_id,
    progress=progress,
    current_frame=current_frame,
    total_frames=total_frames,
    fps=render_fps,
    eta_seconds=eta,
    elapsed_seconds=elapsed,
)

logger.info("render_job_completed",
    job_id=job_id,
    project_id=project_id,
    output_path=output_path,
    file_size_bytes=file_size,
    elapsed_seconds=elapsed,
    render_speed=f"{speed:.1f}x realtime",
    encoder=encoder_name,
    hardware_accelerated=hw_accel,
)

logger.warning("render_job_failed",
    job_id=job_id,
    error=str(e),
    error_code=error_code,
    ffmpeg_stderr=stderr_tail,      # last 500 chars of stderr
    elapsed_seconds=elapsed,
    retry_count=retry_count,
    max_retries=max_retries,
    will_retry=retry_count < max_retries,
)

logger.info("render_job_cancelled",
    job_id=job_id,
    progress_at_cancel=progress,
    elapsed_seconds=elapsed,
    temp_files_cleaned=cleaned,
)

logger.info("render_job_retried",
    job_id=job_id,
    retry_count=retry_count,
    previous_error=previous_error,
)
```

### Hardware Detection Events

```python
logger.info("hardware_encoder_detection_started",
    ffmpeg_path=ffmpeg_path,
)

logger.info("hardware_encoder_detected",
    encoder_name=name,
    encoder_type=encoder_type,
    priority=priority,
)

logger.info("hardware_encoder_detection_complete",
    total_encoders=total,
    hw_encoders=hw_count,
    sw_encoders=sw_count,
    detection_time_ms=elapsed_ms,
)

logger.warning("hardware_encoder_detection_failed",
    error=str(e),
    message="Falling back to software encoders only",
)
```

### Resource Management Events

```python
logger.info("render_disk_space_check",
    output_dir=output_dir,
    free_bytes=free_bytes,
    estimated_output_bytes=estimated,
    sufficient=free_bytes > estimated + min_free,
)

logger.warning("render_disk_space_low",
    output_dir=output_dir,
    free_bytes=free_bytes,
    min_free_bytes=min_free,
    message="Disk space below minimum threshold",
)

logger.info("render_temp_cleanup",
    job_id=job_id,
    files_removed=count,
    bytes_freed=freed,
)

logger.info("render_checkpoint_saved",
    job_id=job_id,
    segment_index=segment_index,
    completed_segments=completed,
    total_segments=total,
)

logger.info("render_job_recovered",
    job_id=job_id,
    resumed_from_segment=segment_index,
    completed_segments=completed,
    total_segments=total,
)
```

### Queue Events

```python
logger.info("render_queue_job_queued",
    job_id=job_id,
    queue_position=position,
    queue_depth=depth,
    max_depth=max_depth,
)

logger.warning("render_queue_full",
    queue_depth=depth,
    max_depth=max_depth,
    rejected_job_id=job_id,
)

logger.info("render_queue_job_dequeued",
    job_id=job_id,
    wait_time_seconds=wait_time,
    active_renders=active,
    max_concurrent=max_concurrent,
)
```

## Prometheus Metrics

### Render Job Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Job lifecycle
render_jobs_total = Counter(
    "video_editor_render_jobs_total",
    "Total render jobs by status",
    ["status", "output_format", "quality_preset"],
)

render_jobs_active = Gauge(
    "video_editor_render_jobs_active",
    "Currently active render jobs",
)

# Render performance
render_duration_seconds = Histogram(
    "video_editor_render_duration_seconds",
    "Time to complete render job",
    ["output_format", "quality_preset", "hardware_accelerated"],
    buckets=[10, 30, 60, 120, 300, 600, 1200, 3600, 7200],
)

render_speed_ratio = Histogram(
    "video_editor_render_speed_ratio",
    "Render speed as multiple of realtime (>1.0 is faster than realtime)",
    ["encoder"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0],
)

render_fps = Gauge(
    "video_editor_render_fps",
    "Current render speed in frames per second",
    ["job_id"],
)

# Output metrics
render_output_bytes = Histogram(
    "video_editor_render_output_bytes",
    "Output file size in bytes",
    ["output_format"],
    buckets=[1e6, 10e6, 50e6, 100e6, 500e6, 1e9, 5e9],
)

# Error metrics
render_errors_total = Counter(
    "video_editor_render_errors_total",
    "Render errors by type",
    ["error_type"],  # ffmpeg_error, timeout, disk_full, cancelled
)

render_retries_total = Counter(
    "video_editor_render_retries_total",
    "Render retry attempts",
)
```

### Queue Metrics

```python
render_queue_depth = Gauge(
    "video_editor_render_queue_depth",
    "Current render queue depth (pending jobs)",
)

render_queue_wait_seconds = Histogram(
    "video_editor_render_queue_wait_seconds",
    "Time jobs wait in queue before starting",
    buckets=[1, 5, 10, 30, 60, 300, 600],
)

render_queue_rejections_total = Counter(
    "video_editor_render_queue_rejections_total",
    "Queue full rejection count",
)
```

### Hardware Encoder Metrics

```python
render_hw_encoder_available = Gauge(
    "video_editor_render_hw_encoder_available",
    "Whether hardware encoder is available",
    ["encoder_name", "encoder_type"],
)

render_hw_fallback_total = Counter(
    "video_editor_render_hw_fallback_total",
    "Times software fallback was used when HW was preferred",
    ["reason"],  # hw_unavailable, hw_error, format_unsupported
)
```

### Resource Metrics

```python
render_disk_free_bytes = Gauge(
    "video_editor_render_disk_free_bytes",
    "Free disk space in render output directory",
)

render_disk_usage_bytes = Gauge(
    "video_editor_render_disk_usage_bytes",
    "Total disk used by render outputs and temp files",
)
```

## Health Checks

### Render Subsystem Health

Extend the existing `/health/ready` endpoint with render checks:

```python
@app.get("/health/ready")
async def readiness():
    checks = {
        # ... existing checks (database, ffmpeg, rust_core, preview, proxy) ...

        "render": {
            "status": "ok",
            "active_jobs": render_service.active_count(),
            "queue_depth": render_service.queue_depth(),
            "max_concurrent": settings.render_max_concurrent,
            "disk_free_bytes": disk_free_bytes,
            "disk_sufficient": disk_free_bytes > settings.render_min_free_disk_bytes,
            "hw_accel_available": hw_detection.has_hw_encoders(),
        },
    }

    # Render is degraded if disk is low
    if disk_free_bytes < settings.render_min_free_disk_bytes:
        checks["render"]["status"] = "degraded"
        checks["render"]["message"] = "Disk space below minimum threshold"

    # Render is degraded if queue is near capacity
    if render_service.queue_depth() > settings.render_max_queue_depth * 0.8:
        checks["render"]["status"] = "degraded"
        checks["render"]["message"] = "Queue approaching capacity"

    # Render unavailable if FFmpeg missing
    if not ffmpeg_available:
        checks["render"]["status"] = "unavailable"
        checks["render"]["message"] = "FFmpeg not found"

    # Render degraded (not failed) doesn't make app unhealthy
    overall = "ok"
    if any(c.get("status") == "unavailable" for c in checks.values()
           if c is not checks.get("render")):
        overall = "degraded"

    return {"status": overall, "checks": checks}
```

### Key principle: Render queue state is informational

The render subsystem health is separate from the API health. Render being unavailable (no FFmpeg) doesn't make the API unhealthy — users can still browse, edit timelines, etc. Only report degraded/unavailable status in the render-specific check.

## Graceful Degradation

### When FFmpeg Is Unavailable

| Subsystem | Behavior | HTTP Response |
|-----------|----------|---------------|
| Render | Refuse to start new jobs | 503 with `FFMPEG_UNAVAILABLE` |
| Queue | Accept but don't start (drain on FFmpeg recovery) | 202 (queued with warning) |
| Encoders | Return empty list, software-only | 200 with empty `hw_encoders` |
| Health check | Report render as `unavailable` | 200 (app is still healthy) |

### When Disk Space Is Low

1. Check disk before starting each render job
2. If below `render_min_free_disk_bytes`, refuse new renders with 507
3. Log warning with disk state
4. Existing active renders continue (they already passed the check)
5. Queue continues to accept jobs but they'll fail pre-flight when dequeued

### When Hardware Encoder Fails Mid-Render

1. Log the HW encoder failure with FFmpeg stderr
2. If `retry_count < max_retries`, retry with software fallback
3. Mark HW encoder as temporarily unavailable
4. Increment `render_hw_fallback_total` metric
5. Next render auto-selects software encoder

### FFmpeg Process Management

```python
async def lifespan(app):
    # ... existing startup ...
    render_service = RenderService(...)
    app.state.render_service = render_service

    # Detect hardware encoders at startup
    await render_service.detect_encoders()

    # Recover interrupted render jobs from checkpoint table
    await render_service.recover_interrupted_jobs()

    yield

    # Graceful shutdown: cancel active renders
    logger.info("render_shutdown_started",
        active_jobs=render_service.active_count(),
        pending_jobs=render_service.queue_depth(),
    )
    await render_service.cancel_all_active()
    await render_service.cleanup_temp_files()
    logger.info("render_shutdown_complete")
```

### Render Timeout

Each render job has a configurable timeout (`render_timeout_seconds`, default 2 hours). When exceeded:
1. Send SIGTERM to FFmpeg process
2. Wait 5 seconds for graceful exit
3. Send SIGKILL if still running
4. Mark job as failed with `RENDER_TIMEOUT` error code
5. Save checkpoint for potential recovery
6. Clean up temp files

## Operational Configuration

All render settings are externalized via pydantic-settings (environment variables):

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Output dir | `SF_RENDER_OUTPUT_DIR` | data/renders | Render output directory |
| Temp dir | `SF_RENDER_TEMP_DIR` | data/renders/temp | Temporary render files |
| Max concurrent | `SF_RENDER_MAX_CONCURRENT` | 2 | Simultaneous render jobs (ge=1, le=8) |
| Max queue depth | `SF_RENDER_MAX_QUEUE_DEPTH` | 20 | Pending jobs before rejection (ge=1, le=100) |
| Timeout | `SF_RENDER_TIMEOUT_SECONDS` | 7200 | Per-job timeout (ge=300, le=86400) |
| Max retries | `SF_RENDER_RETRY_MAX_ATTEMPTS` | 2 | Retry count for transient failures (ge=0, le=5) |
| Retry delay | `SF_RENDER_RETRY_DELAY_SECONDS` | 30 | Delay between retries (ge=5, le=300) |
| Cleanup hours | `SF_RENDER_CLEANUP_HOURS` | 24 | Remove completed job metadata after N hours |
| Default format | `SF_RENDER_DEFAULT_FORMAT` | mp4 | Default output format |
| Default quality | `SF_RENDER_DEFAULT_QUALITY` | high | Default quality preset |
| Default width | `SF_RENDER_DEFAULT_WIDTH` | 1920 | Default output width (ge=320, le=7680) |
| Default height | `SF_RENDER_DEFAULT_HEIGHT` | 1080 | Default output height (ge=240, le=4320) |
| Default FPS | `SF_RENDER_DEFAULT_FPS` | 30.0 | Default frame rate (ge=1.0, le=120.0) |
| Default video bitrate | `SF_RENDER_DEFAULT_VIDEO_BITRATE` | 8000000 | Default video bitrate in bps |
| Default audio bitrate | `SF_RENDER_DEFAULT_AUDIO_BITRATE` | 192000 | Default audio bitrate in bps |
| Two-pass default | `SF_RENDER_TWO_PASS_DEFAULT` | true | Two-pass enabled by default for "high" quality preset |
| HW accel enabled | `SF_RENDER_HW_ACCEL_ENABLED` | true | Attempt hardware detection |
| HW accel prefer | `SF_RENDER_HW_ACCEL_PREFER` | null | Force specific encoder type |
| Parallel min duration | `SF_RENDER_PARALLEL_MIN_DURATION_SECONDS` | 300 | Min timeline duration (seconds) to activate parallel segment rendering (ge=60) |
| Segment duration | `SF_RENDER_SEGMENT_DURATION_SECONDS` | 30 | Segment length in seconds when parallel rendering active (ge=10, le=120) |
| Min free disk | `SF_RENDER_MIN_FREE_DISK_BYTES` | 1073741824 | Min free disk to start render (ge=104857600) |

All settings should be added to `.env.example` with documentation.

## Rate Limiting

Render endpoints have natural rate limiting via queue depth:
- `POST /render` is rejected with 429 when queue is full
- No additional per-IP rate limiting needed for single-user deployment
- The `max_concurrent` setting prevents resource exhaustion from parallel FFmpeg processes
