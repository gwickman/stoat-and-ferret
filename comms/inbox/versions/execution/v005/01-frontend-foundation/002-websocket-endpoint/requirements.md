# Requirements - 002: WebSocket Endpoint

## Goal

Implement a `/ws` WebSocket endpoint with ConnectionManager for event broadcasting, heartbeat support, and correlation ID inclusion in messages.

## Background

M1.10 requires real-time event broadcasting for health status updates and activity feeds. No WebSocket support exists in the current FastAPI app. Without WebSocket support, the GUI must resort to polling, creating unnecessary load and delayed feedback. The ConnectionManager pattern follows the existing DI approach via `create_app()` (LRN-005).

**Backlog Item:** BL-029

## Functional Requirements

**FR-001: WebSocket endpoint**
Create a `/ws` WebSocket endpoint that accepts connections with proper handshake.
- AC: WebSocket connection established at `/ws` with successful handshake

**FR-002: ConnectionManager**
Implement a `ConnectionManager` class with `connect()`, `disconnect()`, and `broadcast()` methods. Use `set()` for O(1) add/remove. Inject via `create_app(ws_manager=...)`.
- AC: ConnectionManager manages active connections and broadcasts messages to all connected clients

**FR-003: Health status broadcasting**
Broadcast health status changes to all connected WebSocket clients.
- AC: Health status changes are received by all connected clients in real time

**FR-004: Activity event broadcasting**
Broadcast activity events (scan started/completed, project created) to all connected clients.
- AC: Activity events are received by all connected clients in real time

**FR-005: Correlation ID support**
Include correlation IDs from existing `CorrelationIdMiddleware` in WebSocket messages.
- AC: WebSocket messages contain a `correlation_id` field

**FR-006: Connection lifecycle**
Handle connection lifecycle: connect, disconnect, and reconnect scenarios. Clean up dead connections during broadcast.
- AC: Dead connections are removed during broadcast; reconnection works without server restart

**FR-007: Heartbeat**
Support configurable heartbeat interval (default 30s) for keepalive.
- AC: Server sends periodic heartbeat messages at the configured interval

## Non-Functional Requirements

**NFR-001: Broadcast latency**
Events broadcast to all connected clients within 100ms of occurrence.
- Metric: Time from event emission to client receipt < 100ms on localhost

**NFR-002: Connection capacity**
Support at least 10 concurrent WebSocket connections (single-user local app, multiple browser tabs).
- Metric: 10 simultaneous connections maintained without errors

## Out of Scope

- WebSocket authentication (single-user local app)
- Message queuing or persistence
- WebSocket compression
- Rate limiting

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests | ConnectionManager: connect adds to set, disconnect removes, broadcast sends to all, dead connections cleaned up |
| Integration tests | WebSocket handshake at `/ws`; receive health status broadcast; receive activity event broadcast; correlation ID present in messages; reconnect after disconnect |
| Contract tests | WebSocket message schema validation (type, payload, correlation_id fields) |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.