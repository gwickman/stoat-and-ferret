# WebSocket Router

**Source:** `src/stoat_ferret/api/routers/ws.py`
**Component:** API Gateway

## Purpose

WebSocket endpoint for real-time event broadcasting. Handles connection acceptance, heartbeat maintenance, and graceful disconnection.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| WS | /ws | WebSocket event stream |

### Functions

- `websocket_endpoint(websocket: WebSocket) -> None`: Handles WebSocket connections at /ws. Accepts connection via ConnectionManager, starts heartbeat task, listens for incoming messages until disconnect.

- `_heartbeat_loop(ws: WebSocket, interval: float) -> None`: Sends periodic heartbeat messages at specified interval (seconds) to keep connection alive and detect dead connections.

## Key Implementation Details

- **Connection lifecycle**: Manager.connect() accepts connection and registers it in the active set; Manager.disconnect() removes it on closure
- **Heartbeat mechanism**: Separate asyncio task sends heartbeat every N seconds (Settings.ws_heartbeat_interval, default 30)
- **Message handling**: Endpoint listens for receive_text() but discards incoming messages; primarily a broadcast channel
- **Graceful shutdown**: On WebSocketDisconnect or exception, heartbeat task is cancelled and connection removed from manager
- **Event format**: Heartbeat events are built via build_event(EventType.HEARTBEAT) which includes timestamp and correlation_id
- **Async safety**: Uses asyncio.create_task() for heartbeat; properly cancels on exit via heartbeat_task.cancel()

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.settings.get_settings`: Settings for heartbeat interval
- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder
- `stoat_ferret.api.websocket.manager.ConnectionManager`: Connection management

### External Dependencies

- `starlette.websockets.WebSocket, WebSocketDisconnect`: WebSocket handling
- `asyncio.sleep, asyncio.create_task`: Async operations
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via add_websocket_route()
- **Used by**: Routers (projects, effects, compose, audio, timeline) for broadcasting events
