# Middleware Stack

## Goal
Add correlation ID and Prometheus metrics middleware.

## Requirements

### FR-001: Correlation ID Middleware
- Generate UUID for each request
- Add `X-Correlation-ID` header to response
- Store in contextvars for logging access

### FR-002: Metrics Middleware
- Count requests by method, path, status
- Measure request duration histogram
- Expose at `/metrics` endpoint

### FR-003: Logging Integration
- Log correlation ID with each request
- Use structlog for structured logging

### FR-004: Dependencies
Add to pyproject.toml:
- `prometheus_client>=0.19`
- `structlog>=24.0`

## Acceptance Criteria
- [ ] All responses have `X-Correlation-ID` header
- [ ] `/metrics` returns Prometheus format
- [ ] Request logs include correlation ID