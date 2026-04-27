"""Prometheus metrics middleware for request monitoring.

Also registers the Phase 6 service-level metrics (BL-288):

- ``stoat_seed_duration_seconds`` (Histogram) — duration of POST
  ``/api/v1/testing/seed`` invocations.
- ``stoat_system_state_duration_seconds`` (Histogram) — duration of GET
  ``/api/v1/system/state`` invocations.
- ``stoat_ws_buffer_size`` (Gauge) — current size of the WebSocket
  replay deque.
- ``stoat_ws_connected_clients`` (Gauge) — currently connected WebSocket
  clients.
- ``stoat_active_jobs_count`` (Gauge) — jobs currently in a non-terminal
  state on the asyncio job queue, labelled by ``job_type``.
- ``stoat_feature_flag_state`` (Gauge) — current STOAT_* feature flag
  values as 0/1, labelled by ``flag``.
- ``stoat_migration_duration_seconds`` (Histogram) — duration of an
  Alembic ``upgrade`` invocation, labelled by ``result`` (``success`` or
  ``failure``).

These metrics are module-level singletons so importing this module from
multiple call sites yields the same instances. The Prometheus client
default registry is shared with :func:`prometheus_client.make_asgi_app`,
so registration here is sufficient for them to appear at GET
``/metrics``.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

# --- Phase 6 service metrics (BL-288) ----------------------------------

# Latency-style histograms keep the prometheus-client default bucket
# layout (5ms..10s) — appropriate for sub-second API endpoints. Migration
# durations can be longer, so use coarser buckets up to 1 hour.

stoat_seed_duration_seconds = Histogram(
    "stoat_seed_duration_seconds",
    "Duration of POST /api/v1/testing/seed in seconds.",
)

stoat_system_state_duration_seconds = Histogram(
    "stoat_system_state_duration_seconds",
    "Duration of GET /api/v1/system/state in seconds.",
)

stoat_ws_buffer_size = Gauge(
    "stoat_ws_buffer_size",
    "Current number of events buffered in the WebSocket replay deque.",
)

stoat_ws_connected_clients = Gauge(
    "stoat_ws_connected_clients",
    "Number of currently connected WebSocket clients.",
)

stoat_active_jobs_count = Gauge(
    "stoat_active_jobs_count",
    "Number of asyncio job queue entries in a non-terminal state.",
    ["job_type"],
)

stoat_feature_flag_state = Gauge(
    "stoat_feature_flag_state",
    "Current value of a STOAT_* feature flag (0=off, 1=on).",
    ["flag"],
)

stoat_migration_duration_seconds = Histogram(
    "stoat_migration_duration_seconds",
    "Duration of an Alembic upgrade in seconds.",
    ["result"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0, 1800.0, 3600.0),
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect Prometheus metrics for HTTP requests.

    Tracks:
    - http_requests_total: Counter by method, path, status
    - http_request_duration_seconds: Histogram by method, path
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and record metrics.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/route handler.

        Returns:
            The response from downstream handlers.
        """
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        path = request.url.path

        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=response.status_code,
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method,
            path=path,
        ).observe(duration)

        return response
