# Metrics Middleware

**Source:** `src/stoat_ferret/api/middleware/metrics.py`
**Component:** API Gateway

## Purpose

Middleware for collecting Prometheus metrics on HTTP requests. Tracks request count and duration by method/path for observability and performance monitoring.

## Public Interface

### Classes

- `MetricsMiddleware(BaseHTTPMiddleware)`: Starlette middleware that:
  - Records request start time
  - Passes request through downstream handlers
  - Increments request count and observes duration
  - Returns response to caller
  - `dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response`: Processes request and records metrics

### Variables

- `REQUEST_COUNT: Counter`: Prometheus counter tracking total HTTP requests, labeled by method, path, and status code
- `REQUEST_DURATION: Histogram`: Prometheus histogram tracking HTTP request duration in seconds, labeled by method and path

## Key Implementation Details

- **Timing**: Uses `time.perf_counter()` for high-resolution timing (nanosecond precision)
- **Labels**: Metrics are partitioned by request method and URL path for granular monitoring
- **Status tracking**: REQUEST_COUNT includes HTTP status code label for success/error breakdowns
- **Order**: Middleware executes after CorrelationIdMiddleware (added to stack second), so metrics reflect full request processing including downstream handlers

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `prometheus_client.Counter`: Prometheus counter metric
- `prometheus_client.Histogram`: Prometheus histogram metric
- `starlette.middleware.base.BaseHTTPMiddleware`: Base middleware class
- `starlette.requests.Request`: HTTP request object
- `starlette.responses.Response`: HTTP response object
- `time.perf_counter`: High-resolution timer

## Relationships

- **Used by**: `app.py` (added to middleware stack)
- **Exposed via**: `/metrics` endpoint (prometheus_client ASGI app)
