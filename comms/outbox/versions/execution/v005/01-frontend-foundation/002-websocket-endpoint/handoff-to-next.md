# Handoff: 002-websocket-endpoint -> next feature

## What Was Built

- `ConnectionManager` class in `src/stoat_ferret/api/websocket/manager.py` with `connect()`, `disconnect()`, `broadcast()` methods
- `EventType` enum and `build_event()` helper in `src/stoat_ferret/api/websocket/events.py`
- `/ws` WebSocket endpoint in `src/stoat_ferret/api/routers/ws.py` with heartbeat support
- DI integration: `create_app(ws_manager=...)` stores manager on `app.state.ws_manager`

## How to Use

### Broadcasting events from any endpoint

```python
from stoat_ferret.api.websocket.events import EventType, build_event

# Inside a route handler with access to request:
ws_manager = request.app.state.ws_manager
event = build_event(EventType.SCAN_COMPLETED, {"scanned": 5, "new": 3})
await ws_manager.broadcast(event)
```

### Testing with WebSocket

```python
from stoat_ferret.api.websocket.manager import ConnectionManager

manager = ConnectionManager()
app = create_app(ws_manager=manager, ...)
```

## Integration Points for Next Features

- Scan endpoints (`POST /api/v1/videos/scan`) can emit `SCAN_STARTED` / `SCAN_COMPLETED` events via the ws_manager
- Project creation (`POST /api/v1/projects`) can emit `PROJECT_CREATED` events
- Health endpoint can emit `HEALTH_STATUS` events when status changes
- The `ws_manager` is available on `app.state.ws_manager` in all request handlers

## Key Design Decisions

- Heartbeat interval is 30s (configurable via `DEFAULT_HEARTBEAT_INTERVAL` constant)
- Dead connections are cleaned up lazily during broadcast (not via periodic scan)
- `asyncio.Lock` protects broadcast from concurrent modification
- Correlation ID is read from the existing `CorrelationIdMiddleware` context var
