# Phase 4: Observability & Operations

## Overview

Phase 4 introduces significant new subsystems (preview, proxy, HLS serving, cache management) that all require observability and operational excellence. This document defines structured logging events, Prometheus metrics, health checks, and graceful degradation patterns for the preview and playback subsystem.

## Structured Logging Events

All events use structlog with correlation IDs per existing pattern. Events follow the convention: `{subsystem}_{action}_{result}`.

### Preview Session Events

```python
# Preview lifecycle
logger.info("preview_session_created",
    session_id=session_id,
    project_id=project_id,
    quality=quality,
    estimated_segments=segments_total,
)

logger.info("preview_generation_started",
    session_id=session_id,
    ffmpeg_command=command_str,  # full command for debugging
    filter_cost=filter_cost,     # from Rust estimate_filter_cost
    simplified=True,             # whether simplification was applied
)

logger.info("preview_segment_generated",
    session_id=session_id,
    segment_index=index,
    segments_total=total,
    elapsed_ms=elapsed,
)

logger.info("preview_ready",
    session_id=session_id,
    project_id=project_id,
    total_segments=segments_total,
    generation_time_seconds=elapsed,
    manifest_path=manifest_path,
)

logger.info("preview_seek_requested",
    session_id=session_id,
    from_position=current_pos,
    to_position=seek_pos,
)

logger.warning("preview_generation_failed",
    session_id=session_id,
    error=str(e),
    ffmpeg_stderr=stderr_tail,  # last 500 chars of stderr
)

logger.info("preview_session_expired",
    session_id=session_id,
    age_seconds=age,
    segments_cleaned=segment_count,
    bytes_freed=bytes_freed,
)
```

### Proxy Events

```python
logger.info("proxy_generation_started",
    video_id=video_id,
    source_resolution=f"{width}x{height}",
    target_quality=quality,
    source_file=source_path,
)

logger.info("proxy_generation_complete",
    video_id=video_id,
    quality=quality,
    output_size_bytes=file_size,
    generation_time_seconds=elapsed,
    compression_ratio=source_size / file_size,
)

logger.warning("proxy_generation_failed",
    video_id=video_id,
    error=str(e),
    ffmpeg_exit_code=exit_code,
)

logger.info("proxy_stale_detected",
    video_id=video_id,
    proxy_checksum=proxy_checksum,
    source_checksum=current_checksum,
    message="Source file modified after proxy generation",
)
```

### Cache Events

```python
logger.info("preview_cache_eviction",
    evicted_session_id=session_id,
    eviction_reason="lru",      # or "ttl_expired", "manual"
    freed_bytes=freed,
    cache_usage_after=usage_percent,
)

logger.warning("preview_cache_full",
    current_bytes=current,
    max_bytes=max_bytes,
    active_sessions=count,
    message="Cache at capacity, oldest session will be evicted",
)
```

### Thumbnail/Waveform Events

```python
logger.info("thumbnail_strip_generated",
    video_id=video_id,
    frame_count=frame_count,
    interval_seconds=interval,
    strip_size_bytes=size,
    generation_time_seconds=elapsed,
)

logger.info("waveform_generated",
    video_id=video_id,
    format=format,
    duration_seconds=duration,
    channels=channels,
    generation_time_seconds=elapsed,
)
```

## Prometheus Metrics

### Preview Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Session lifecycle
preview_sessions_total = Counter(
    "video_editor_preview_sessions_total",
    "Total preview sessions created",
    ["quality"],
)

preview_sessions_active = Gauge(
    "video_editor_preview_sessions_active",
    "Currently active preview sessions",
)

# Generation performance
preview_generation_seconds = Histogram(
    "video_editor_preview_generation_seconds",
    "Time to generate complete preview (all segments)",
    ["quality"],
    buckets=[1, 2, 5, 10, 20, 30, 60, 120],
)

preview_segment_generation_seconds = Histogram(
    "video_editor_preview_segment_seconds",
    "Time to generate a single HLS segment",
    buckets=[0.1, 0.5, 1, 2, 5, 10],
)

preview_seek_latency_seconds = Histogram(
    "video_editor_preview_seek_latency_seconds",
    "Time from seek request to segments available",
    buckets=[0.1, 0.5, 1, 2, 5],
)

# Errors
preview_errors_total = Counter(
    "video_editor_preview_errors_total",
    "Preview generation errors",
    ["error_type"],  # ffmpeg_error, timeout, cache_full
)
```

### Proxy Metrics

```python
proxy_generation_seconds = Histogram(
    "video_editor_proxy_generation_seconds",
    "Time to generate proxy file",
    ["quality"],
    buckets=[5, 10, 30, 60, 120, 300],
)

proxy_files_total = Gauge(
    "video_editor_proxy_files_total",
    "Total proxy files by status",
    ["status"],  # ready, pending, failed, stale
)

proxy_storage_bytes = Gauge(
    "video_editor_proxy_storage_bytes",
    "Total proxy storage used in bytes",
)
```

### Cache Metrics

```python
preview_cache_bytes = Gauge(
    "video_editor_preview_cache_bytes",
    "Current preview cache usage in bytes",
)

preview_cache_max_bytes = Gauge(
    "video_editor_preview_cache_max_bytes",
    "Maximum preview cache size in bytes",
)

preview_cache_evictions_total = Counter(
    "video_editor_preview_cache_evictions_total",
    "Total cache evictions",
    ["reason"],  # lru, ttl_expired, manual
)

preview_cache_hit_ratio = Gauge(
    "video_editor_preview_cache_hit_ratio",
    "Preview cache hit ratio (0.0-1.0)",
)
```

### Thumbnail/Waveform Metrics

```python
thumbnail_generation_seconds = Histogram(
    "video_editor_thumbnail_generation_seconds",
    "Time to generate thumbnail strip",
    buckets=[1, 2, 5, 10, 30],
)

waveform_generation_seconds = Histogram(
    "video_editor_waveform_generation_seconds",
    "Time to generate waveform",
    ["format"],
    buckets=[1, 2, 5, 10, 30],
)
```

## Health Checks

### Preview Subsystem Health

Extend the existing `/health/ready` endpoint with preview checks:

```python
@app.get("/health/ready")
async def readiness():
    checks = {
        # ... existing checks (database, ffmpeg, rust_core) ...

        "preview": {
            "status": "ok",
            "active_sessions": preview_manager.active_count(),
            "cache_usage_percent": preview_cache.usage_percent(),
            "cache_healthy": preview_cache.usage_percent() < 90,
        },
        "proxy": {
            "status": "ok",
            "proxy_dir_writable": os.access(settings.proxy_output_dir, os.W_OK),
            "pending_proxies": proxy_service.pending_count(),
        },
    }

    # Preview is degraded (not failed) if cache is >90% full
    if preview_cache.usage_percent() >= 90:
        checks["preview"]["status"] = "degraded"
        checks["preview"]["message"] = "Cache near capacity, eviction may affect performance"

    # Preview is unavailable if FFmpeg is missing
    if not ffmpeg_available:
        checks["preview"]["status"] = "unavailable"
        checks["preview"]["message"] = "FFmpeg not found, preview disabled"

    overall = "ok"
    if any(c.get("status") == "unavailable" for c in checks.values()):
        overall = "degraded"  # preview unavailable doesn't make whole app unhealthy

    return {"status": overall, "checks": checks}
```

### Key principle: Preview is optional

The preview subsystem should never cause the overall application to report as unhealthy. If FFmpeg is unavailable or the cache is full, preview endpoints return appropriate errors (503, 507) but the rest of the application continues normally.

## Graceful Degradation

### When FFmpeg Is Unavailable

| Subsystem | Behavior | HTTP Response |
|-----------|----------|---------------|
| Preview | Refuse to start new sessions | 503 with `FFMPEG_UNAVAILABLE` |
| Proxy | Skip auto-generation on scan | Log warning, continue scan |
| Thumbnails | Return placeholder image | 200 with default placeholder |
| Waveforms | Return empty data | 200 with `{"samples": []}` |
| Render | Fail with clear error | 503 with `FFMPEG_UNAVAILABLE` |
| Health check | Report preview as `unavailable` | 200 (app is still healthy) |

### When Cache Is Full

1. Attempt LRU eviction of oldest session
2. If eviction frees enough space, proceed
3. If not, return 507 `PREVIEW_CACHE_FULL`
4. Log warning with current cache state
5. Never block other operations

### When Proxy Is Missing

1. Preview falls back to source file (higher quality, slower)
2. Log info event noting proxy fallback
3. Include `proxy_used: false` in preview response
4. Auto-queue proxy generation for future previews

### FFmpeg Process Cleanup on Shutdown

```python
async def lifespan(app):
    # ... existing startup ...
    preview_manager = PreviewManager(...)
    app.state.preview_manager = preview_manager

    yield

    # Graceful shutdown: cancel active previews
    logger.info("preview_shutdown_started",
        active_sessions=preview_manager.active_count(),
    )
    await preview_manager.cancel_all()
    await preview_manager.cleanup_temp_files()
    logger.info("preview_shutdown_complete")
```

## Operational Configuration

All preview/proxy settings are externalized via pydantic-settings (environment variables):

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Preview cache max | `SF_PREVIEW_CACHE_MAX_BYTES` | 1073741824 (1GB) | Maximum preview cache size |
| Preview max sessions | `SF_PREVIEW_CACHE_MAX_SESSIONS` | 5 | Max concurrent preview sessions |
| Preview TTL | `SF_PREVIEW_SESSION_TTL_SECONDS` | 3600 | Session timeout |
| HLS segment duration | `SF_PREVIEW_SEGMENT_DURATION` | 4.0 | Seconds per HLS segment |
| Proxy auto-generate | `SF_PROXY_AUTO_GENERATE` | true | Generate proxies on scan |
| Proxy output dir | `SF_PROXY_OUTPUT_DIR` | data/proxies | Proxy file storage path |
| Proxy max concurrent | `SF_PROXY_MAX_CONCURRENT` | 2 | Max concurrent proxy jobs |
| Thumbnail interval | `SF_THUMBNAIL_STRIP_INTERVAL` | 5.0 | Seconds between strip frames |
| Waveform samples/sec | `SF_WAVEFORM_SAMPLES_PER_SECOND` | 10 | Audio waveform resolution |

All settings should be added to `.env.example` with documentation.
