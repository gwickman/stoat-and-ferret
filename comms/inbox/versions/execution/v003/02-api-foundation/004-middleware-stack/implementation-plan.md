# Implementation Plan: Middleware Stack

## Step 1: Add Dependencies
Update `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing
    "prometheus_client>=0.19",
    "structlog>=24.0",
]
```

## Step 2: Create Correlation ID Middleware
Create `src/stoat_ferret/api/middleware/correlation.py`:

```python
"""Correlation ID middleware."""

import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to each request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
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
    """Get current correlation ID."""
    return correlation_id_var.get()
```

## Step 3: Create Metrics Middleware
Create `src/stoat_ferret/api/middleware/metrics.py`:

```python
"""Prometheus metrics middleware."""

import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect Prometheus metrics for requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
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
```

## Step 4: Update Application Factory
Update `src/stoat_ferret/api/app.py`:

```python
from prometheus_client import make_asgi_app

from stoat_ferret.api.middleware.correlation import CorrelationIdMiddleware
from stoat_ferret.api.middleware.metrics import MetricsMiddleware

def create_app() -> FastAPI:
    # ... existing code
    
    # Add middleware (order matters - first added = outermost)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    
    # Mount metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    return app
```

## Step 5: Add Tests
Create `tests/test_api/test_middleware.py`:

```python
"""Tests for middleware stack."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_correlation_id_generated(client: TestClient):
    """Requests without correlation ID get one generated."""
    response = client.get("/health/live")
    assert "X-Correlation-ID" in response.headers
    # Should be a valid UUID
    assert len(response.headers["X-Correlation-ID"]) == 36


@pytest.mark.api
def test_correlation_id_preserved(client: TestClient):
    """Requests with correlation ID have it preserved."""
    response = client.get(
        "/health/live",
        headers={"X-Correlation-ID": "test-correlation-id"},
    )
    assert response.headers["X-Correlation-ID"] == "test-correlation-id"


@pytest.mark.api
def test_metrics_endpoint(client: TestClient):
    """Metrics endpoint returns Prometheus format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
```

## Verification
- Response headers include `X-Correlation-ID`
- `curl http://localhost:8000/metrics` returns Prometheus format