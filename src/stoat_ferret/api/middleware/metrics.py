"""Prometheus metrics middleware for request monitoring."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from prometheus_client import Counter, Histogram
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
