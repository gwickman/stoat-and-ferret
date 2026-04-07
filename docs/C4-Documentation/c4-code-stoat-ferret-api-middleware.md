# C4 Code Level: API Middleware

## Overview

- **Name**: Middleware Layer for HTTP Request Instrumentation
- **Description**: Provides request tracing, correlation IDs, and Prometheus metrics collection for all HTTP requests.
- **Location**: `src/stoat_ferret/api/middleware/`
- **Language**: Python
- **Purpose**: Cross-cutting concerns for HTTP request/response instrumentation, distributed request tracing, and operational metrics.
- **Parent Component**: [API Gateway](./c4-component-api-gateway.md)

## Code Elements

### Classes

#### `CorrelationIdMiddleware`
- **Location**: `correlation.py`
- **Base Class**: `BaseHTTPMiddleware` (from Starlette)
- **Purpose**: Extracts or generates correlation IDs for request tracing, stores in context var, and appends to response headers.
- **Methods**:
  - `async dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response`
    - Extracts `X-Correlation-ID` header or generates UUID
    - Stores ID in `correlation_id_var` context for access during request
    - Adds ID to response headers

#### `MetricsMiddleware`
- **Location**: `metrics.py`
- **Base Class**: `BaseHTTPMiddleware` (from Starlette)
- **Purpose**: Collects Prometheus metrics (request count and duration) for all HTTP requests.
- **Methods**:
  - `async dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response`
    - Records request start time
    - Increments request counter with method/path/status labels
    - Records request duration histogram with method/path labels

### Functions

- `get_correlation_id() -> str`
  - **Location**: `correlation.py:52-58`
  - **Purpose**: Retrieves current correlation ID from context var
  - **Returns**: Correlation ID string or empty string if none set

### Module-Level Variables

#### Metrics (metrics.py)
- `REQUEST_COUNT: Counter`
  - Prometheus counter tracking total HTTP requests by method, path, status
- `REQUEST_DURATION: Histogram`
  - Prometheus histogram tracking HTTP request duration in seconds by method, path

#### Context Variables (correlation.py)
- `correlation_id_var: ContextVar[str]`
  - Stores current request's correlation ID for access during request processing
  - Default value: empty string

### Type Aliases

- `RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]`
  - Function type for Starlette middleware call_next parameter

## Dependencies

### Internal Dependencies
- None (self-contained middleware)

### External Dependencies
- **starlette**: `BaseHTTPMiddleware`, `Request`, `Response` classes
- **prometheus_client**: `Counter`, `Histogram` metric types
- **contextvars**: `ContextVar` for context-local storage
- **uuid**: UUID generation for correlation IDs
- **time**: Performance timing for metrics

## Relationships

```mermaid
---
title: Middleware Module Structure
---
classDiagram
    namespace Middleware {
        class CorrelationIdMiddleware {
            +dispatch(request: Request, call_next: RequestResponseEndpoint) Response
        }
        class MetricsMiddleware {
            +dispatch(request: Request, call_next: RequestResponseEndpoint) Response
        }
        class CorrelationIdModule {
            <<module>>
            +get_correlation_id() str
            -correlation_id_var ContextVar~str~
        }
        class MetricsModule {
            <<module>>
            -REQUEST_COUNT Counter
            -REQUEST_DURATION Histogram
        }
    }

    CorrelationIdMiddleware --> CorrelationIdModule : calls
    MetricsMiddleware --> MetricsModule : updates
    CorrelationIdMiddleware ..|> StarletteMW : extends
    MetricsMiddleware ..|> StarletteMW : extends
    
    StarletteMW[Starlette BaseHTTPMiddleware]
```

## Notes

- Both middleware classes follow Starlette's `BaseHTTPMiddleware` pattern for request/response interception
- Correlation IDs enable distributed request tracing across service boundaries
- Prometheus metrics are collected in-memory and exposed for scraping by monitoring systems
- Context variables (correlation_id_var) are request-scoped and safe for concurrent requests
