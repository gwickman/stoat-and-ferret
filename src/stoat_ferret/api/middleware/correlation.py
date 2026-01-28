"""Correlation ID middleware for request tracing."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to each request for tracing.

    The middleware will:
    1. Extract existing X-Correlation-ID header or generate a new UUID
    2. Store the ID in a contextvar for access during request processing
    3. Add the ID to the response headers
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and add correlation ID.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/route handler.

        Returns:
            Response with X-Correlation-ID header.
        """
        # Get from header or generate new
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Store in context for logging
        correlation_id_var.set(correlation_id)

        # Process request
        response = await call_next(request)

        # Add to response header
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def get_correlation_id() -> str:
    """Get current correlation ID from context.

    Returns:
        The correlation ID for the current request, or empty string if none.
    """
    return correlation_id_var.get()
