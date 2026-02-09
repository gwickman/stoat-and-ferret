"""Unit tests for ConnectionManager and event types."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from starlette.websockets import WebSocketState

from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager


def _make_mock_ws(*, connected: bool = True) -> AsyncMock:
    """Create a mock WebSocket object.

    Args:
        connected: Whether the mock should report as connected.

    Returns:
        Mock WebSocket with send_json and client_state.
    """
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED if connected else WebSocketState.DISCONNECTED
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestConnectionManager:
    """Tests for ConnectionManager connect/disconnect/broadcast."""

    async def test_connect_adds_to_set(self) -> None:
        """Connect should accept the websocket and add it to active connections."""
        manager = ConnectionManager()
        ws = _make_mock_ws()

        await manager.connect(ws)

        ws.accept.assert_awaited_once()
        assert manager.active_connections == 1

    async def test_disconnect_removes_from_set(self) -> None:
        """Disconnect should remove the websocket from active connections."""
        manager = ConnectionManager()
        ws = _make_mock_ws()
        await manager.connect(ws)

        manager.disconnect(ws)

        assert manager.active_connections == 0

    async def test_disconnect_unknown_is_noop(self) -> None:
        """Disconnecting an unknown websocket should not raise."""
        manager = ConnectionManager()
        ws = _make_mock_ws()

        manager.disconnect(ws)  # Should not raise

        assert manager.active_connections == 0

    async def test_broadcast_sends_to_all(self) -> None:
        """Broadcast should send the message to all connected clients."""
        manager = ConnectionManager()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        message = {"type": "test", "payload": {}}

        await manager.broadcast(message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_awaited_once_with(message)

    async def test_broadcast_removes_dead_connections(self) -> None:
        """Broadcast should remove connections that fail to send."""
        manager = ConnectionManager()
        ws_alive = _make_mock_ws()
        ws_dead = _make_mock_ws()
        ws_dead.send_json.side_effect = RuntimeError("connection closed")
        await manager.connect(ws_alive)
        await manager.connect(ws_dead)

        await manager.broadcast({"type": "test"})

        assert manager.active_connections == 1

    async def test_broadcast_removes_disconnected_state(self) -> None:
        """Broadcast should remove connections with DISCONNECTED state."""
        manager = ConnectionManager()
        ws_alive = _make_mock_ws()
        ws_gone = _make_mock_ws(connected=False)
        await manager.connect(ws_alive)
        await manager.connect(ws_gone)

        await manager.broadcast({"type": "test"})

        assert manager.active_connections == 1
        ws_gone.send_json.assert_not_awaited()

    async def test_broadcast_empty_no_error(self) -> None:
        """Broadcasting with no connections should not raise."""
        manager = ConnectionManager()

        await manager.broadcast({"type": "test"})  # Should not raise


class TestEventTypes:
    """Tests for event type definitions and message building."""

    def test_event_type_values(self) -> None:
        """All expected event types should exist with correct string values."""
        assert EventType.HEALTH_STATUS.value == "health_status"
        assert EventType.SCAN_STARTED.value == "scan_started"
        assert EventType.SCAN_COMPLETED.value == "scan_completed"
        assert EventType.PROJECT_CREATED.value == "project_created"
        assert EventType.HEARTBEAT.value == "heartbeat"

    def test_build_event_schema(self) -> None:
        """build_event should return dict with type, payload, correlation_id, timestamp."""
        event = build_event(EventType.HEALTH_STATUS, {"status": "ok"})

        assert event["type"] == "health_status"
        assert event["payload"] == {"status": "ok"}
        assert "correlation_id" in event
        assert "timestamp" in event

    def test_build_event_default_payload(self) -> None:
        """build_event with no payload should use empty dict."""
        event = build_event(EventType.HEARTBEAT)

        assert event["payload"] == {}

    def test_build_event_explicit_correlation_id(self) -> None:
        """build_event should use explicit correlation_id when provided."""
        event = build_event(
            EventType.SCAN_STARTED,
            correlation_id="test-corr-123",
        )

        assert event["correlation_id"] == "test-corr-123"

    def test_build_event_reads_context_var(self) -> None:
        """build_event should read correlation_id from context var when not provided."""
        with patch(
            "stoat_ferret.api.websocket.events.get_correlation_id",
            return_value="ctx-corr-456",
        ):
            event = build_event(EventType.PROJECT_CREATED)

        assert event["correlation_id"] == "ctx-corr-456"

    def test_build_event_empty_correlation_id(self) -> None:
        """build_event should return None correlation_id when context var is empty."""
        with patch(
            "stoat_ferret.api.websocket.events.get_correlation_id",
            return_value="",
        ):
            event = build_event(EventType.HEARTBEAT)

        assert event["correlation_id"] is None
