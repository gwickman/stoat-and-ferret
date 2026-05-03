"""Integration tests for WebSocket client identity feature (BL-315).

Covers connection lifecycle with subscribe_token, token validation,
reconnection, and Last-Event-ID backwards compatibility.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from stoat_ferret.api.app import create_app
from stoat_ferret.api.websocket.events import EventType, build_event, reset_event_counters
from stoat_ferret.api.websocket.identity import InMemoryClientIdentityStore, generate_client_id
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


@pytest.fixture(autouse=True)
def _isolate_counters() -> None:
    """Reset event-id counters so each test starts from event-00000."""
    reset_event_counters()


@pytest.fixture
def identity_store() -> InMemoryClientIdentityStore:
    """Provide a fresh identity store for each test."""
    return InMemoryClientIdentityStore()


@pytest.fixture
def ws_manager(identity_store: InMemoryClientIdentityStore) -> ConnectionManager:
    """Provide a ConnectionManager wired to the identity store fixture."""
    return ConnectionManager(client_identity_store=identity_store)


@pytest.fixture
def ws_app(ws_manager: ConnectionManager, identity_store: InMemoryClientIdentityStore) -> FastAPI:
    """Build a FastAPI app with injected manager and identity store."""
    return create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        job_queue=InMemoryJobQueue(),
        ws_manager=ws_manager,
        client_identity_store=identity_store,
    )


@pytest.fixture
def ws_client(ws_app: FastAPI) -> Generator[TestClient, None, None]:
    """Yield a TestClient against the fixture app."""
    with TestClient(ws_app) as c:
        yield c


class TestTokenValidation:
    """AC-001: subscribe_token extraction and format validation."""

    def test_connect_with_valid_token_stores_identity(
        self, ws_client: TestClient, identity_store: InMemoryClientIdentityStore
    ) -> None:
        """Valid 32-char hex token causes identity entry to be stored on connect."""
        token = generate_client_id()
        with ws_client.websocket_connect(f"/ws?subscribe_token={token}"):
            entry = identity_store.retrieve(token)
            assert entry is not None
            assert entry["client_id"] == token

    def test_connect_with_invalid_token_rejects_with_4400(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Non-32-char-hex subscribe_token is rejected with close code 4400."""
        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            ws_client.websocket_connect("/ws?subscribe_token=badtoken"),
        ):
            pass
        assert exc_info.value.code == 4400
        assert ws_manager.active_connections == 0

    def test_connect_with_wrong_length_token_rejects_with_4400(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Token that is wrong length (not 32 chars) is rejected with 4400."""
        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            ws_client.websocket_connect("/ws?subscribe_token=abc123"),
        ):
            pass
        assert exc_info.value.code == 4400
        assert ws_manager.active_connections == 0

    def test_connect_without_token_proceeds_normally(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Missing subscribe_token does not block connection (Last-Event-ID path)."""
        with ws_client.websocket_connect("/ws"):
            assert ws_manager.active_connections == 1

    def test_invalid_token_not_added_to_connections(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Rejected connection (4400) is never added to _connections."""
        initial = ws_manager.active_connections
        with (
            pytest.raises(WebSocketDisconnect),
            ws_client.websocket_connect("/ws?subscribe_token=tooshort"),
        ):
            pass
        assert ws_manager.active_connections == initial


class TestConnectionLifecycle:
    """AC-002, AC-003: identity stored on connect, cleared on disconnect."""

    def test_identity_stored_on_connect(
        self, ws_client: TestClient, identity_store: InMemoryClientIdentityStore
    ) -> None:
        """Identity entry is present while connection is active."""
        token = generate_client_id()
        with ws_client.websocket_connect(f"/ws?subscribe_token={token}"):
            assert identity_store.retrieve(token) is not None

    def test_identity_cleared_on_disconnect(
        self, ws_client: TestClient, identity_store: InMemoryClientIdentityStore
    ) -> None:
        """Identity entry is removed after WebSocket disconnects."""
        token = generate_client_id()
        with ws_client.websocket_connect(f"/ws?subscribe_token={token}"):
            pass  # disconnect happens on context exit
        assert identity_store.retrieve(token) is None

    def test_no_identity_stored_without_token(
        self, ws_client: TestClient, identity_store: InMemoryClientIdentityStore
    ) -> None:
        """Connection without token does not create identity entries."""
        with ws_client.websocket_connect("/ws"):
            # No specific token to check — just confirm connect/disconnect work
            pass
        # Verify store is still empty (no phantom entries)
        # InMemoryClientIdentityStore stores in _store dict; verify no entries
        assert not identity_store._store  # type: ignore[attr-defined]

    def test_reconnect_with_same_token_stores_identity_again(
        self, ws_client: TestClient, identity_store: InMemoryClientIdentityStore
    ) -> None:
        """After disconnect, reconnecting with same token creates a fresh identity entry."""
        token = generate_client_id()
        # First connection
        with ws_client.websocket_connect(f"/ws?subscribe_token={token}"):
            assert identity_store.retrieve(token) is not None
        # After disconnect, identity is cleared
        assert identity_store.retrieve(token) is None
        # Reconnect with same token
        with ws_client.websocket_connect(f"/ws?subscribe_token={token}"):
            assert identity_store.retrieve(token) is not None

    def test_concurrent_connections_same_token_last_connect_wins(
        self, ws_client: TestClient, identity_store: InMemoryClientIdentityStore
    ) -> None:
        """Two connections with the same token; last-connect overwrites the entry."""
        token = generate_client_id()
        with ws_client.websocket_connect(f"/ws?subscribe_token={token}"):
            entry_first = identity_store.retrieve(token)
            assert entry_first is not None
            # Second connection with same token while first is still open
            with ws_client.websocket_connect(f"/ws?subscribe_token={token}"):
                entry_second = identity_store.retrieve(token)
                assert entry_second is not None
                # Entry exists; both connections are in _connections
                # The store() call from the second connect updated last_seen
                assert entry_second["last_seen"] >= entry_first["last_seen"]


class TestBackwardsCompatibility:
    """AC-004: Last-Event-ID path unchanged when no subscribe_token present."""

    def test_last_event_id_replay_without_token(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Client without token receives buffered events via Last-Event-ID header."""
        # Broadcast 3 events while no client is connected
        events = [build_event(EventType.JOB_PROGRESS, job_id="job-compat") for _ in range(3)]
        for event in events:
            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

        # Reconnect without token, using Last-Event-ID of first event
        first_id = events[0]["event_id"]
        with ws_client.websocket_connect(
            "/ws",
            headers={"last-event-id": first_id},
        ) as ws:
            # Should receive events[1] and events[2] (replay after first_id)
            msg1 = ws.receive_json()
            msg2 = ws.receive_json()

        assert msg1["event_id"] == events[1]["event_id"]
        assert msg2["event_id"] == events[2]["event_id"]

    def test_last_event_id_replay_with_token(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """Client with valid token still receives Last-Event-ID replay."""
        token = generate_client_id()
        events = [build_event(EventType.JOB_PROGRESS, job_id="job-token-compat") for _ in range(3)]
        for event in events:
            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast(event))

        first_id = events[0]["event_id"]
        with ws_client.websocket_connect(
            f"/ws?subscribe_token={token}",
            headers={"last-event-id": first_id},
        ) as ws:
            msg1 = ws.receive_json()
            msg2 = ws.receive_json()

        assert msg1["event_id"] == events[1]["event_id"]
        assert msg2["event_id"] == events[2]["event_id"]

    def test_active_connections_zero_after_no_token_disconnect(
        self, ws_client: TestClient, ws_manager: ConnectionManager
    ) -> None:
        """No-token connection properly decrements active_connections on exit."""
        with ws_client.websocket_connect("/ws"):
            assert ws_manager.active_connections == 1
        assert ws_manager.active_connections == 0
