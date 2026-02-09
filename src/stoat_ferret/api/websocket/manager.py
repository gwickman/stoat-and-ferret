"""ConnectionManager for WebSocket connection lifecycle and broadcasting."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from starlette.websockets import WebSocket, WebSocketState

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manage active WebSocket connections and broadcast messages.

    Uses a set for O(1) add/remove of connections. Dead connections
    are cleaned up automatically during broadcast.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def active_connections(self) -> int:
        """Return the number of active connections."""
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept and track.
        """
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("websocket_connected", active=len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from tracking.

        Args:
            websocket: The WebSocket connection to remove.
        """
        self._connections.discard(websocket)
        logger.info("websocket_disconnected", active=len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to all connected clients.

        Dead connections are removed automatically. Uses a lock to
        prevent concurrent modification of the connection set.

        Args:
            message: JSON-serializable dict to send to all clients.
        """
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._connections:
                try:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_json(message)
                    else:
                        dead.append(ws)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.discard(ws)
                logger.info("websocket_dead_connection_removed", active=len(self._connections))
