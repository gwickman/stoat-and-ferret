# Implementation Plan - 002: WebSocket Endpoint

## Overview

Implement a `/ws` WebSocket endpoint with a `ConnectionManager` class for managing connections and broadcasting events. Integrate with the existing DI pattern via `create_app()` and include correlation IDs from the existing middleware.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/websocket/__init__.py` | Create | Package init |
| `src/stoat_ferret/api/websocket/manager.py` | Create | ConnectionManager class |
| `src/stoat_ferret/api/websocket/events.py` | Create | Event type definitions and schemas |
| `src/stoat_ferret/api/routers/ws.py` | Create | WebSocket endpoint router |
| `src/stoat_ferret/api/app.py` | Modify | Add `ws_manager` param to `create_app()`, register WS route, init in lifespan |
| `tests/test_websocket.py` | Create | ConnectionManager unit tests |
| `tests/test_ws_endpoint.py` | Create | WebSocket endpoint integration tests |

## Implementation Stages

### Stage 1: ConnectionManager

1. Create `ConnectionManager` class with `set[WebSocket]` for active connections
2. Implement `connect(websocket)`: accept and add to set
3. Implement `disconnect(websocket)`: discard from set
4. Implement `broadcast(message: dict)`: send to all, clean up dead connections with try/except
5. Add `asyncio.Lock` for thread-safe broadcast

**Verification:**
```bash
uv run pytest tests/test_websocket.py -v
```

### Stage 2: Event Types

1. Define event type enum: `health_status`, `scan_started`, `scan_completed`, `project_created`
2. Define message schema: `{"type": str, "payload": dict, "correlation_id": str | None, "timestamp": str}`
3. Create helper function to build event messages with correlation ID from context var

**Verification:**
```bash
uv run pytest tests/test_websocket.py -v
```

### Stage 3: WebSocket Endpoint

1. Create `/ws` endpoint in `ws.py` router
2. Accept connection via ConnectionManager
3. Implement receive loop for client messages (heartbeat pong)
4. Handle `WebSocketDisconnect` for cleanup
5. Add heartbeat task: send periodic ping at configured interval

**Verification:**
```bash
uv run pytest tests/test_ws_endpoint.py -v
```

### Stage 4: App Integration

1. Add `ws_manager: ConnectionManager | None = None` parameter to `create_app()`
2. Store on `app.state.ws_manager`
3. Create ConnectionManager in lifespan if not injected
4. Register WebSocket router
5. Add broadcast calls to scan handler and project creation endpoints

**Verification:**
```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/
```

## Test Infrastructure Updates

- ConnectionManager unit tests with mock WebSocket objects
- Integration tests using FastAPI `TestClient` WebSocket support
- Contract tests validating message schema

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- **R-3 (WebSocket stability):** Local app minimizes network issues. 30s heartbeat with client reconnect handles browser tab backgrounding. See risk assessment.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: add WebSocket endpoint with ConnectionManager and event broadcasting

- Implement ConnectionManager with connect/disconnect/broadcast
- Add /ws endpoint with heartbeat and correlation ID support
- Define event types for health, scan, and project events
- Integrate with create_app() DI pattern and lifespan

Implements BL-029
```