"""Integration tests for the /ws WebSocket endpoint."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


@pytest.fixture
def ws_manager() -> ConnectionManager:
    """Create a ConnectionManager for testing.

    Returns:
        Fresh ConnectionManager instance.
    """
    return ConnectionManager()


@pytest.fixture
def ws_app(ws_manager: ConnectionManager) -> FastAPI:
    """Create test app with WebSocket manager injected.

    Args:
        ws_manager: ConnectionManager fixture.

    Returns:
        Configured FastAPI application for WebSocket testing.
    """
    return create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        job_queue=InMemoryJobQueue(),
        ws_manager=ws_manager,
    )


@pytest.fixture
def ws_client(ws_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for WebSocket testing.

    Args:
        ws_app: FastAPI application fixture.

    Yields:
        Test client for making WebSocket requests.
    """
    with TestClient(ws_app) as c:
        yield c


class TestWebSocketHandshake:
    """Tests for WebSocket connection handshake."""

    def test_connect_succeeds(self, ws_client: TestClient) -> None:
        """WebSocket connection should be established at /ws."""
        with ws_client.websocket_connect("/ws"):
            pass  # Connection accepted without error

    def test_connect_increments_active(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Connecting should increment active connections count."""
        with ws_client.websocket_connect("/ws"):
            assert ws_manager.active_connections == 1

    def test_disconnect_decrements_active(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Disconnecting should decrement active connections count."""
        with ws_client.websocket_connect("/ws"):
            assert ws_manager.active_connections == 1
        assert ws_manager.active_connections == 0


class TestWebSocketBroadcast:
    """Tests for receiving broadcast messages via WebSocket."""

    def test_receive_broadcast(self, ws_client: TestClient, ws_manager: ConnectionManager) -> None:
        """Connected client should receive broadcast messages."""
        with ws_client.websocket_connect("/ws") as ws:
            event = build_event(
                EventType.HEALTH_STATUS,
                {"status": "ok"},
                correlation_id="test-123",
            )

            import asyncio

            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

            data = ws.receive_json()
            assert data["type"] == "health_status"
            assert data["payload"] == {"status": "ok"}
            assert data["correlation_id"] == "test-123"

    def test_receive_activity_event(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Connected client should receive activity event broadcasts."""
        with ws_client.websocket_connect("/ws") as ws:
            event = build_event(
                EventType.SCAN_COMPLETED,
                {"scanned": 5, "new": 3},
                correlation_id="scan-456",
            )

            import asyncio

            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

            data = ws.receive_json()
            assert data["type"] == "scan_completed"
            assert data["payload"]["scanned"] == 5


class TestWebSocketMessageSchema:
    """Contract tests for WebSocket message schema."""

    def test_message_has_required_fields(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """WebSocket messages must contain type, payload, correlation_id, timestamp."""
        with ws_client.websocket_connect("/ws") as ws:
            event = build_event(
                EventType.PROJECT_CREATED,
                {"project_id": "p-1"},
                correlation_id="corr-789",
            )

            import asyncio

            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

            data = ws.receive_json()
            assert "type" in data
            assert "payload" in data
            assert "correlation_id" in data
            assert "timestamp" in data

    def test_type_is_string(self, ws_client: TestClient, ws_manager: ConnectionManager) -> None:
        """Message type field must be a string."""
        with ws_client.websocket_connect("/ws") as ws:
            event = build_event(EventType.HEARTBEAT, correlation_id="x")

            import asyncio

            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

            data = ws.receive_json()
            assert isinstance(data["type"], str)

    def test_payload_is_dict(self, ws_client: TestClient, ws_manager: ConnectionManager) -> None:
        """Message payload field must be a dict."""
        with ws_client.websocket_connect("/ws") as ws:
            event = build_event(EventType.HEARTBEAT, correlation_id="x")

            import asyncio

            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

            data = ws.receive_json()
            assert isinstance(data["payload"], dict)

    def test_timestamp_is_iso_format(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Message timestamp must be an ISO 8601 string."""
        with ws_client.websocket_connect("/ws") as ws:
            event = build_event(EventType.HEARTBEAT, correlation_id="x")

            import asyncio

            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

            data = ws.receive_json()
            from datetime import datetime

            # Should parse without error
            datetime.fromisoformat(data["timestamp"])


class TestWebSocketReconnect:
    """Tests for reconnection after disconnect."""

    def test_reconnect_after_disconnect(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Client should be able to reconnect after disconnect."""
        # First connection
        with ws_client.websocket_connect("/ws"):
            assert ws_manager.active_connections == 1
        assert ws_manager.active_connections == 0

        # Reconnect
        with ws_client.websocket_connect("/ws"):
            assert ws_manager.active_connections == 1
