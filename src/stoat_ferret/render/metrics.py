"""Prometheus metrics for render pipeline monitoring.

Provides metrics for tracking render job lifecycle including:
- Job counters by status (completed, failed, cancelled)
- Duration histograms with render-appropriate bucket boundaries
- Speed ratio gauge for real-time vs wall-clock rendering
- Queue depth gauge for active/pending job counts
- Hardware encoder active gauge
- Disk usage gauge for render output directory
"""

from prometheus_client import Counter, Gauge, Histogram

render_jobs_total = Counter(
    "stoat_ferret_render_jobs_total",
    "Total render jobs by status",
    ["status"],  # submitted, completed, failed, cancelled
)

render_duration_seconds = Histogram(
    "stoat_ferret_render_duration_seconds",
    "Render job duration in seconds",
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600, float("inf")],
)

render_speed_ratio = Gauge(
    "stoat_ferret_render_speed_ratio",
    "Render speed ratio (total_duration_s / wall_clock_s)",
)

render_queue_depth = Gauge(
    "stoat_ferret_render_queue_depth",
    "Current number of queued render jobs",
)

render_encoder_active = Gauge(
    "stoat_ferret_render_encoder_active",
    "Number of active hardware encoder instances",
    ["encoder_name"],
)

render_disk_usage_bytes = Gauge(
    "stoat_ferret_render_disk_usage_bytes",
    "Render output directory disk usage in bytes",
)
