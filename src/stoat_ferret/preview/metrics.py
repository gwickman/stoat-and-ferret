"""Prometheus metrics for preview, proxy, and cache subsystems.

Defines module-level metric singletons matching the observability design spec.
Histogram buckets are tuned for each operation's expected latency profile.
"""

from prometheus_client import Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# Preview session metrics
# ---------------------------------------------------------------------------

preview_sessions_total = Counter(
    "video_editor_preview_sessions_total",
    "Total preview sessions created",
    ["quality"],
)

preview_sessions_active = Gauge(
    "video_editor_preview_sessions_active",
    "Currently active preview sessions",
)

preview_generation_seconds = Histogram(
    "video_editor_preview_generation_seconds",
    "Time to generate complete preview (all segments)",
    ["quality"],
    buckets=[1, 2, 5, 10, 20, 30, 60, 120],
)

preview_segment_seconds = Histogram(
    "video_editor_preview_segment_seconds",
    "Time to generate a single HLS segment",
    buckets=[0.1, 0.5, 1, 2, 5, 10],
)

preview_seek_latency_seconds = Histogram(
    "video_editor_preview_seek_latency_seconds",
    "Time from seek request to segments available",
    buckets=[0.1, 0.5, 1, 2, 5],
)

preview_errors_total = Counter(
    "video_editor_preview_errors_total",
    "Preview generation errors",
    ["error_type"],
)

# ---------------------------------------------------------------------------
# Proxy metrics
# ---------------------------------------------------------------------------

proxy_generation_seconds = Histogram(
    "video_editor_proxy_generation_seconds",
    "Time to generate proxy file",
    ["quality"],
    buckets=[5, 10, 30, 60, 120, 300],
)

proxy_files_total = Gauge(
    "video_editor_proxy_files_total",
    "Total proxy files by status",
    ["status"],
)

proxy_storage_bytes = Gauge(
    "video_editor_proxy_storage_bytes",
    "Total proxy storage used in bytes",
)

proxy_evictions_total = Counter(
    "video_editor_proxy_evictions_total",
    "Total proxy cache evictions",
    ["reason"],
)

# ---------------------------------------------------------------------------
# Cache metrics
# ---------------------------------------------------------------------------

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
    ["reason"],
)

preview_cache_hit_ratio = Gauge(
    "video_editor_preview_cache_hit_ratio",
    "Preview cache hit ratio (0.0-1.0)",
)
