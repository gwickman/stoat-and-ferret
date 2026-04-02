# Render Metrics

**Source:** `src/stoat_ferret/render/metrics.py`
**Component:** Render Engine

## Purpose

Defines Prometheus metrics for the render subsystem as module-level singletons, following the metric singleton module pattern (LRN-137). Provides a single inventory of all render instrumentation points.

## Public Interface

### Module-Level Constants

- `render_jobs_total`: `Counter(labels=["status"])` — Total render jobs by outcome status ("completed", "failed", "cancelled")
- `render_duration_seconds`: `Histogram(buckets=[10, 30, 60, 120, 300, 600, 1800, 3600])` — Render job duration distribution
- `render_speed_ratio`: `Gauge()` — Current render speed as (total_duration * progress) / wall_clock_time
- `render_queue_depth`: `Gauge()` — Current number of queued (waiting) render jobs
- `render_encoder_active`: `Gauge(labels=["encoder_name"])` — Active hardware encoder tracking by name
- `render_disk_usage_bytes`: `Gauge()` — Render output directory disk usage

## Dependencies

### External Dependencies

- `prometheus_client`: Counter, Histogram, Gauge metric types

## Key Implementation Details

### Metric Singleton Module Pattern (LRN-137)

All Prometheus metrics are defined as module-level constants in this dedicated file. Service modules (`service.py`, `executor.py`, `queue.py`) import specific metric objects rather than creating them inline. This pattern:
- Provides a single inventory of all render instrumentation
- Avoids import-time side effects in service code
- Prevents duplicate metric registration errors
- Matches the pattern used by FFmpeg Integration and Preview subsystems

### Histogram Buckets

`render_duration_seconds` uses render-specific buckets: 10s, 30s, 1min, 2min, 5min, 10min, 30min, 1hr — reflecting the wide range of render job durations.

### Speed Ratio

`render_speed_ratio` is a Gauge (not a Counter) because the speed ratio fluctuates during rendering. A value > 1.0 means faster than real-time; < 1.0 means slower than real-time.

## Relationships

- **Used by:** RenderService (render_jobs_total, render_duration_seconds), RenderExecutor (render_speed_ratio, render_encoder_active), RenderQueue (render_queue_depth), API Gateway health router (render_disk_usage_bytes)
- **Exposed via:** Prometheus metrics endpoint at `/metrics`
