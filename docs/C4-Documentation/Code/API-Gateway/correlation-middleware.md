# Correlation ID Middleware

**Source:** `src/stoat_ferret/api/middleware/correlation.py`
**Component:** API Gateway

## Purpose

Middleware for distributed request tracing. Extracts or generates a unique X-Correlation-ID header for each request, stores it in a context variable for access during request processing, and includes it in response headers for end-to-end tracking.

## Public Interface

### Classes

- `CorrelationIdMiddleware(BaseHTTPMiddleware)`: Starlette middleware that:
  - Extracts `X-Correlation-ID` header from request or generates new UUID
  - Stores ID in `correlation_id_var` context variable
  - Adds ID to response headers
  - `dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response`: Processes request and returns response with correlation ID header

### Variables

- `correlation_id_var: ContextVar[str]`: Thread-safe context variable storing correlation ID for current request (default: "")

### Functions

- `get_correlation_id() -> str`: Returns current correlation ID from context variable, or empty string if none

## Key Implementation Details

- **Header extraction or generation**: If `X-Correlation-ID` header is present, reuse it; otherwise generate new UUID4
- **Context variable storage**: Stores ID in contextvars.ContextVar for access in async code without passing as parameter
- **Request/response handling**: Adds ID to both incoming context (via set) and outgoing headers
- **Async-safe**: Uses async dispatch method; context variables are async-safe

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `starlette.middleware.base.BaseHTTPMiddleware`: Base middleware class
- `starlette.requests.Request`: HTTP request object
- `starlette.responses.Response`: HTTP response object
- `contextvars.ContextVar`: Thread-safe context variable for async contexts
- `uuid`: UUID generation

## Relationships

- **Used by**: `app.py` (added to middleware stack)
- **Used in**: WebSocket events, routers (via `get_correlation_id()`) for structured logging
