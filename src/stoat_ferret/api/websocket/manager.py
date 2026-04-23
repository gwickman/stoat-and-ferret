"""ConnectionManager for WebSocket connection lifecycle and broadcasting."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from starlette.websockets import WebSocket, WebSocketState

from stoat_ferret.api.settings import get_settings

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manage active WebSocket connections and broadcast messages.

    Uses a set for O(1) add/remove of connections. Dead connections
    are cleaned up automatically during broadcast. Maintains a bounded
    replay buffer of recent broadcasts so reconnecting clients can use
    the ``Last-Event-ID`` handshake header to catch up on missed events
    (BL-274, FR-001..FR-005).
    """

    def __init__(
        self,
        *,
        buffer_size: int | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Initialize the manager with a bounded replay buffer.

        Args:
            buffer_size: Maximum number of events retained in the replay
                buffer. Defaults to ``settings.ws_replay_buffer_size``.
                A size of 0 disables buffering (no replay).
            ttl_seconds: Maximum age, in seconds, of replayable events at
                reconnect time. Defaults to ``settings.ws_replay_ttl_seconds``.
        """
        settings = get_settings()
        resolved_size = buffer_size if buffer_size is not None else settings.ws_replay_buffer_size
        resolved_ttl = ttl_seconds if ttl_seconds is not None else settings.ws_replay_ttl_seconds
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._replay_buffer: deque[dict[str, Any]] = deque(maxlen=resolved_size)
        self._buffer_size = resolved_size
        self._ttl_seconds = resolved_ttl

    @property
    def active_connections(self) -> int:
        """Return the number of active connections."""
        return len(self._connections)

    @property
    def replay_buffer_size(self) -> int:
        """Return the configured maximum replay buffer size."""
        return self._buffer_size

    @property
    def replay_ttl_seconds(self) -> int:
        """Return the configured replay event TTL in seconds."""
        return self._ttl_seconds

    @property
    def buffered_event_count(self) -> int:
        """Return the current number of buffered events (for tests/metrics)."""
        return len(self._replay_buffer)

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
        """Send a message to all connected clients and buffer it for replay.

        Dead connections are removed automatically. Uses a lock to
        prevent concurrent modification of the connection set. After
        fanning out to live clients, the message is appended to the
        replay buffer so a later reconnect with ``Last-Event-ID`` can
        retrieve it (FR-001). Oldest events are evicted when the deque
        reaches ``buffer_size`` (INV-005).

        Args:
            message: JSON-serializable dict to send to all clients.
        """
        logger.debug(
            "ws_broadcast",
            event_type=message.get("type", "unknown"),
            client_count=len(self._connections),
        )
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
        if self._buffer_size > 0:
            self._replay_buffer.append(message)

    def replay_since(self, last_event_id: str | None) -> list[dict[str, Any]]:
        """Return buffered events for a reconnecting client, filtered by age and id.

        Behaviour (FR-002..FR-004):
          * Expired events (timestamp older than ``ttl_seconds`` relative
            to now) are excluded first.
          * If ``last_event_id`` is ``None`` or empty, every non-expired
            event is returned.
          * If ``last_event_id`` matches a buffered event, the events
            strictly after it are returned.
          * If ``last_event_id`` is not present in the (non-expired)
            buffer — because it is too old, has been evicted, or is
            ahead of the server — every non-expired event is returned.
          * Results preserve broadcast order (FR-004).

        Args:
            last_event_id: The ``Last-Event-ID`` HTTP header value sent
                by the reconnecting client, or ``None`` when no header
                was supplied.

        Returns:
            List of replayable event dicts in broadcast order.
        """
        if self._buffer_size == 0 or not self._replay_buffer:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._ttl_seconds)
        fresh = [event for event in self._replay_buffer if _event_is_fresh(event, cutoff)]
        if not last_event_id:
            return fresh
        for index, event in enumerate(fresh):
            if event.get("event_id") == last_event_id:
                return fresh[index + 1 :]
        return fresh


def _event_is_fresh(event: dict[str, Any], cutoff: datetime) -> bool:
    """Return True when the event's timestamp is newer than ``cutoff``.

    Events whose ``timestamp`` field is missing or unparseable are
    treated as fresh — this is deliberately lenient: a malformed
    timestamp should not silently drop an event from the replay stream,
    and the deque bound still limits memory.
    """
    raw = event.get("timestamp")
    if not isinstance(raw, str):
        return True
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed >= cutoff
