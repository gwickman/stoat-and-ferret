"""WebSocket endpoint for real-time event broadcasting."""

from __future__ import annotations

import asyncio

import structlog
from starlette.websockets import WebSocket, WebSocketDisconnect

from stoat_ferret.api.settings import get_settings
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.identity import is_valid_client_id
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


async def _replay_missed_events(websocket: WebSocket, manager: ConnectionManager) -> None:
    """Replay buffered events when the client supplies ``Last-Event-ID``.

    Parses the ``Last-Event-ID`` handshake header (case-insensitive) and
    streams every non-expired buffered event after that id in order
    (FR-003, FR-004). Clients that do not send the header are treated as
    fresh subscribers and receive no history. Called once, immediately
    after the WebSocket upgrade completes.

    Args:
        websocket: The freshly accepted WebSocket.
        manager: ConnectionManager holding the shared replay buffer.
    """
    last_event_id = websocket.headers.get("last-event-id")
    if not last_event_id:
        return
    replay = manager.replay_since(last_event_id)
    if not replay:
        return
    logger.info(
        "ws_replay_dispatch",
        last_event_id=last_event_id,
        count=len(replay),
    )
    for event in replay:
        await websocket.send_json(event)


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections at /ws.

    Extracts ``subscribe_token`` from query params. If present and invalid
    (not a 32-char hex string), closes the connection with code 4400 before
    adding it to the manager. Valid tokens are passed through to
    ``ConnectionManager.connect()`` for identity tracking.

    Replays any buffered events the client missed (using the
    ``Last-Event-ID`` header), starts a heartbeat task, and listens for
    incoming messages until disconnect.

    Args:
        websocket: The WebSocket connection.
    """
    manager: ConnectionManager = websocket.app.state.ws_manager

    subscribe_token: str | None = websocket.query_params.get("subscribe_token")
    if subscribe_token is not None and not is_valid_client_id(subscribe_token):
        await websocket.close(code=4400, reason="Invalid subscribe_token format")
        return

    await manager.connect(websocket, client_id=subscribe_token)
    await _replay_missed_events(websocket, manager)

    heartbeat_interval = get_settings().ws_heartbeat_interval
    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket, heartbeat_interval))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket, client_id=subscribe_token)
