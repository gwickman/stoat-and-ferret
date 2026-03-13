# WebSocket Connection Manager

**Source:** `src/stoat_ferret/api/websocket/manager.py`
**Component:** API Gateway

## Purpose

Manages WebSocket connection lifecycle and message broadcasting to all connected clients. Provides thread-safe connection tracking and automatic cleanup of dead connections.

## Public Interface

### Classes

- `ConnectionManager`: Manages active WebSocket connections and broadcasts messages.
  - `__init__() -> None`: Initializes empty connection set and asyncio lock
  - `connect(websocket: WebSocket) -> None`: Accepts connection and registers it
  - `disconnect(websocket: WebSocket) -> None`: Removes connection from tracking
  - `broadcast(message: dict[str, Any]) -> None`: Sends message to all connected clients
  - `active_connections` (property): Returns count of active connections

## Key Implementation Details

- **Connection storage**: Uses set[WebSocket] for O(1) add/remove operations
- **Thread safety**: Uses asyncio.Lock() to prevent concurrent modification during broadcast
- **Dead connection cleanup**: broadcast() automatically removes dead connections (state != CONNECTED or send error)
- **Error handling**: Exceptions during send are caught; connection marked as dead and removed
- **Logging**: Logs connection/disconnection events and dead connection removals with active count
- **No state storage**: Manager tracks connections only; application code handles state/filtering of messages

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `starlette.websockets.WebSocket, WebSocketState`: WebSocket abstractions
- `asyncio.Lock`: Async-safe lock
- `structlog`: Structured logging

## Relationships

- **Used by**: `app.py` (created in lifespan or injected), WebSocket endpoint
- **Used by**: All routers (projects, effects, compose, audio, timeline) for broadcasting events
