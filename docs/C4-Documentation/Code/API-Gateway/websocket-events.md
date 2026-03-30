# WebSocket Events

**Source:** `src/stoat_ferret/api/websocket/events.py`
**Component:** API Gateway

## Purpose

Event type definitions and message schema for WebSocket broadcasting. Provides standardized event format with correlation ID tracking and timestamp.

## Public Interface

### Enums

- `EventType(str, Enum)`: Event types for WebSocket broadcasting:
  - `HEALTH_STATUS`: Health/readiness status changes
  - `SCAN_STARTED`: Directory scan started
  - `SCAN_COMPLETED`: Directory scan completed
  - `PROJECT_CREATED`: New project created
  - `HEARTBEAT`: Periodic heartbeat to keep connection alive
  - `TIMELINE_UPDATED`: Timeline changed (tracks/clips modified)
  - `LAYOUT_APPLIED`: Layout preset applied to project
  - `AUDIO_MIX_CHANGED`: Audio mix configuration changed
  - `TRANSITION_APPLIED`: Transition applied between clips
  - `JOB_PROGRESS`: Background job progress update (proxy, waveform, etc.)
  - `PREVIEW_GENERATING`: Preview session starting HLS generation
  - `PREVIEW_READY`: Preview HLS manifest ready
  - `PREVIEW_SEEKING`: Preview seek position changed
  - `PREVIEW_ERROR`: Preview generation error occurred
  - `AI_ACTION`: AI-assisted action executed
  - `RENDER_PROGRESS`: Batch render job progress update
  - `PROXY_READY`: Proxy video file ready for use

### Functions

- `build_event(event_type: EventType, payload: dict[str, Any] | None=None, correlation_id: str | None=None) -> dict[str, Any]`: Builds WebSocket event message with standard schema. Returns dict with type, payload, correlation_id, and timestamp fields.

## Key Implementation Details

- **Event schema**: All events include:
  - `type`: Event type as string (EventType.value)
  - `payload`: Event-specific data dict (defaults to empty dict)
  - `correlation_id`: Request correlation ID from context or provided override (defaults to None)
  - `timestamp`: ISO 8601 timestamp (UTC)

- **Correlation ID**: Automatically reads from context variable via get_correlation_id() if not explicitly provided; None if no correlation ID in context

- **Timestamp**: Generated at event build time (now UTC)

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.middleware.correlation.get_correlation_id`: Retrieve correlation ID from context

### External Dependencies

- `datetime.datetime, datetime.timezone`: Timestamp generation
- `enum.Enum`: Event type enumeration

## Relationships

- **Used by**: WebSocket endpoint, all routers (projects, effects, compose, audio, timeline, videos) for event broadcasting
- **Used with**: ConnectionManager for sending events to clients
