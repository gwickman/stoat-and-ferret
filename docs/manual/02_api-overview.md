# API Overview

Stoat & Ferret exposes a REST API built with FastAPI, designed for both human developers and AI agents. This guide covers the conventions, error handling, and structure of the API.

## Base URL

```
http://localhost:8000
```

The default host is `127.0.0.1` and port is `8000`. Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `STOAT_API_HOST` | `127.0.0.1` | Server bind address |
| `STOAT_API_PORT` | `8000` | Server port |
| `STOAT_DATABASE_PATH` | `data/stoat.db` | SQLite database file path |
| `STOAT_THUMBNAIL_DIR` | `data/thumbnails` | Thumbnail storage directory |
| `STOAT_GUI_STATIC_PATH` | `gui/dist` | Path to built frontend assets |
| `STOAT_WS_HEARTBEAT_INTERVAL` | `30` | WebSocket heartbeat interval (seconds) |
| `STOAT_ALLOWED_SCAN_ROOTS` | `[]` (all allowed) | Allowed directories for video scanning |
| `STOAT_DEBUG` | `false` | Enable debug mode |
| `STOAT_LOG_LEVEL` | `INFO` | Logging level |

All settings use the `STOAT_` prefix and can also be placed in a `.env` file in the project root.

## Authentication

The current version is designed for **single-user local use** and does not require authentication. All endpoints are accessible without credentials.

## Content Type

All request and response bodies use JSON:

```
Content-Type: application/json
```

The only exception is the thumbnail endpoint (`GET /api/v1/videos/{video_id}/thumbnail`), which returns `image/jpeg`.

## Pagination

List endpoints support pagination with `limit` and `offset` query parameters:

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `limit` | integer | 20 | 1-100 | Maximum items per page |
| `offset` | integer | 0 | 0+ | Number of items to skip |

Example:

```bash
curl "http://localhost:8000/api/v1/videos?limit=10&offset=20"
```

List responses include a `total` field indicating the total number of items available.

## Error Format

All errors follow a consistent JSON structure:

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Resource (video, project, clip, job) not found |
| `INVALID_PATH` | 400 | Scan path is not a valid directory |
| `PATH_NOT_ALLOWED` | 403 | Scan path outside allowed roots |
| `VALIDATION_ERROR` | 400 | Clip validation failed (e.g., out_point exceeds duration) |
| `EFFECT_NOT_FOUND` | 400 | Unknown effect type |
| `INVALID_EFFECT_PARAMS` | 400 | Effect parameters fail schema validation |
| `SAME_CLIP` | 400 | Transition source and target are the same clip |
| `EMPTY_TIMELINE` | 400 | Transition requested on empty timeline |
| `NOT_ADJACENT` | 400 | Transition clips are not adjacent in timeline |

Validation errors from the effects system may include an additional `errors` array with per-field details:

```json
{
  "detail": {
    "code": "INVALID_EFFECT_PARAMS",
    "message": "fontsize: -5 is less than the minimum of 1",
    "errors": [
      {"path": "fontsize", "message": "-5 is less than the minimum of 1"}
    ]
  }
}
```

## Endpoint Groups

| Group | Prefix | Description |
|-------|--------|-------------|
| Health | `/health` | Liveness and readiness probes |
| Videos | `/api/v1/videos` | Video library management |
| Projects | `/api/v1/projects` | Project and clip management |
| Jobs | `/api/v1/jobs` | Async job status polling |
| Effects | `/api/v1/effects`, `/api/v1/projects/.../effects` | Effect discovery and application |
| WebSocket | `/ws` | Real-time event stream |
| Metrics | `/metrics` | Prometheus metrics |
| GUI | `/gui/*` | Web frontend (static files) |

## OpenAPI Documentation

The API is fully documented via OpenAPI 3.x:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) -- interactive explorer with "Try it out" functionality
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc) -- clean, readable documentation
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) -- machine-readable schema for code generation

## Correlation IDs

Every HTTP request is assigned a unique correlation ID via the `X-Correlation-ID` header. If you include this header in your request, the server preserves it; otherwise, a UUID is generated. This ID appears in:

- Response headers
- Structured log entries
- WebSocket event messages

Use correlation IDs to trace requests through logs when debugging.

## WebSocket Events

Connect to `ws://localhost:8000/ws` for real-time events. The server sends:

- **Heartbeat** messages every 30 seconds (configurable)
- Event notifications for scan operations and project creation

Event message format:

```json
{
  "type": "heartbeat",
  "payload": {},
  "correlation_id": null,
  "timestamp": "2025-01-15T10:30:00.000000+00:00"
}
```

Event types: `heartbeat`, `health_status`, `scan_started`, `scan_completed`, `project_created`.

## Next Steps

- [API Reference](03_api-reference.md) -- complete endpoint documentation with curl examples
- [Effects Guide](04_effects-guide.md) -- effects system details
- [Getting Started](01_getting-started.md) -- quick tutorial workflow
