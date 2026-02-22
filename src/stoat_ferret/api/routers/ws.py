"""WebSocket endpoint for real-time event broadcasting."""

from __future__ import annotations

import asyncio

import structlog
from starlette.websockets import WebSocket, WebSocketDisconnect

from stoat_ferret.api.settings import get_settings
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager

logger = structlog.get_logger(__name__)


async def _heartbeat_loop(ws: WebSocket, interval: float) -> None:
    """Send periodic heartbeat messages to keep the connection alive.

    Args:
        ws: The WebSocket connection.
        interval: Seconds between heartbeat messages.
    """
    while True:
        await asyncio.sleep(interval)
        await ws.send_json(build_event(EventType.HEARTBEAT))


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections at /ws.

    Accepts the connection via ConnectionManager, starts a heartbeat
    task, and listens for incoming messages until disconnect.

    Args:
        websocket: The WebSocket connection.
    """
    manager: ConnectionManager = websocket.app.state.ws_manager
    await manager.connect(websocket)

    heartbeat_interval = get_settings().ws_heartbeat_interval
    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket, heartbeat_interval))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket)
