# C4 Code Level: API WebSocket

## Overview

- **Name**: API WebSocket Layer
- **Description**: WebSocket connection management and real-time event broadcasting infrastructure.
- **Location**: `src/stoat_ferret/api/websocket/`
- **Language**: Python
- **Purpose**: Provide typed event definitions and connection lifecycle management for real-time client updates. Handles WebSocket connection registry, message broadcast to all connected clients, and automatic cleanup of dead connections.
- **Parent Component**: [API Gateway](./c4-component-api-gateway.md)

## Code Elements

### Functions/Methods

#### events.py

- `build_event(event_type: EventType, payload: dict[str, Any] | None = None, correlation_id: str | None = None) -> dict[str, Any]`
  - Description: Build standardized WebSocket event message with type, payload, correlation ID, and ISO timestamp.
  - Location: events.py:41
  - Dependencies: get_correlation_id, datetime, EventType

### Classes/Modules

#### EventType (events.py:12)

String enumeration defining all WebSocket event types broadcast by the system.

**Enumeration Values:**
- HEALTH_STATUS = "health_status"
- SCAN_STARTED = "scan_started"
- SCAN_COMPLETED = "scan_completed"
- PROJECT_CREATED = "project_created"
- HEARTBEAT = "heartbeat"
- TIMELINE_UPDATED = "timeline_updated"
- LAYOUT_APPLIED = "layout_applied"
- AUDIO_MIX_CHANGED = "audio_mix_changed"
- TRANSITION_APPLIED = "transition_applied"
- JOB_PROGRESS = "job_progress"
- PREVIEW_GENERATING = "preview.generating"
- PREVIEW_READY = "preview.ready"
- PREVIEW_SEEKING = "preview.seeking"
- PREVIEW_ERROR = "preview.error"
- AI_ACTION = "ai_action"
- RENDER_PROGRESS = "render_progress"
- RENDER_STARTED = "render_started"
- RENDER_COMPLETED = "render_completed"
- RENDER_FAILED = "render_failed"
- RENDER_CANCELLED = "render_cancelled"
- RENDER_QUEUED = "render_queued"
- RENDER_FRAME_AVAILABLE = "render_frame_available"
- RENDER_QUEUE_STATUS = "render_queue_status"
- PROXY_READY = "proxy.ready"

**Usage**: Used as event_type parameter in build_event() to specify message category.

#### ConnectionManager (manager.py:14)

Manages active WebSocket connections and broadcasts messages to all connected clients. Uses set for O(1) add/remove operations. Automatically removes dead connections during broadcast.

**Attributes:**
- `_connections: set[WebSocket]` - Active WebSocket connections
- `_lock: asyncio.Lock` - Prevents concurrent modification during broadcast

**Methods:**
- `__init__() -> None` - Initialize empty connection set and create async lock (manager.py:21)
- `@property active_connections() -> int` - Return count of currently connected clients (manager.py:25)
- `async connect(websocket: WebSocket) -> None` - Accept connection and add to registry (manager.py:30)
- `disconnect(websocket: WebSocket) -> None` - Remove connection from registry (manager.py:40)
- `async broadcast(message: dict[str, Any]) -> None` - Send JSON message to all connected clients, removing dead connections automatically (manager.py:49)

**Dependencies:**
- Internal: None
- External: starlette.websockets (WebSocket, WebSocketState), asyncio.Lock, structlog

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.middleware.correlation`: get_correlation_id (reads context var for event tracking)

### External Dependencies

- **starlette.websockets**: WebSocket (connection protocol), WebSocketState (connection state enum)
- **asyncio**: Lock (thread-safe broadcast access), Event (cancellation signals)
- **datetime**: datetime, timezone (ISO timestamp generation)
- **enum**: Enum (EventType base class)
- **structlog**: Structured logging for connection and broadcast events

## Relationships

```mermaid
---
title: Code Diagram for API WebSocket
---
classDiagram
    namespace Events {
        class EventType {
            <<enumeration>>
            HEALTH_STATUS
            SCAN_STARTED
            SCAN_COMPLETED
            JOB_PROGRESS
            PROXY_READY
            RENDER_PROGRESS
            RENDER_COMPLETED
        }
        
        class events_module {
            <<module>>
            +build_event(event_type, payload, correlation_id) dict
        }
    }
    
    namespace Manager {
        class ConnectionManager {
            -_connections set~WebSocket~
            -_lock asyncio.Lock
            +active_connections int
            +connect(ws) void
            +disconnect(ws) void
            +broadcast(message) void
        }
    }
    
    namespace External {
        class WebSocket {
            <<starlette>>
            +accept() void
            +send_json(data) void
            +client_state WebSocketState
        }
        
        class WebSocketState {
            <<enumeration>>
            CONNECTING
            CONNECTED
            DISCONNECTING
            DISCONNECTED
        }
        
        class asyncio_Lock {
            <<asyncio>>
        }
    }
    
    namespace Middleware {
        class correlation_module {
            <<module>>
            +get_correlation_id() str
        }
    }
    
    events_module --> EventType : uses
    events_module --> correlation_module : reads correlation ID
    events_module --> datetime : timestamps
    
    ConnectionManager --> asyncio_Lock : uses for thread safety
    ConnectionManager --> WebSocket : manages set of
    ConnectionManager --> WebSocketState : checks state
    ConnectionManager --> EventType : broadcasts events
    
    WebSocket ..> EventType : receives via broadcast
```

## Notes

- **Thread-safe broadcasting**: ConnectionManager uses asyncio.Lock to ensure thread-safe concurrent access during broadcast operations
- **Dead connection cleanup**: Broadcast automatically removes connections in non-CONNECTED state, filtering failures transparently
- **Event schema**: All events follow the same structure: type, payload, correlation_id, timestamp - enabling consistent client-side handling
- **Correlation tracking**: build_event() reads correlation_id from context var for request tracing across async boundaries
- **Non-blocking**: disconnect() is synchronous (simple set removal); connect() and broadcast() are async for I/O safety
- **Event types**: 24 distinct event types covering scanning, rendering, proxies, timeline edits, and health monitoring
- **Scalability**: Using set for O(1) connection add/remove enables efficient management of many concurrent connections
