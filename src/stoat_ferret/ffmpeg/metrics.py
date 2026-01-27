"""Prometheus metrics for FFmpeg execution monitoring.

Provides metrics for tracking FFmpeg command executions including:
- Total execution counts by status
- Execution duration histograms
- Active process gauges
"""

from prometheus_client import Counter, Gauge, Histogram

ffmpeg_executions_total = Counter(
    "stoat_ferret_ffmpeg_executions_total",
    "Total FFmpeg command executions",
    ["status"],  # success, failure
)

ffmpeg_execution_duration_seconds = Histogram(
    "stoat_ferret_ffmpeg_execution_duration_seconds",
    "FFmpeg command execution duration in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

ffmpeg_active_processes = Gauge(
    "stoat_ferret_ffmpeg_active_processes",
    "Number of currently running FFmpeg processes",
)
