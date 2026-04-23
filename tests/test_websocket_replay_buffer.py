"""Unit tests for the WebSocket replay buffer on ``ConnectionManager`` (BL-274)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from starlette.websockets import WebSocketState

from stoat_ferret.api.websocket.events import EventType, build_event, reset_event_counters
from stoat_ferret.api.websocket.manager import ConnectionManager


@pytest.fixture(autouse=True)
def _isolate_counters() -> None:
    """Reset the module-level event counters between tests."""
    reset_event_counters()


def _make_event(event_id: str, *, timestamp: datetime | None = None) -> dict[str, Any]:
    """Build a minimal event payload with a specific id and timestamp."""
    ts = timestamp if timestamp is not None else datetime.now(timezone.utc)
    return {
        "type": EventType.JOB_PROGRESS.value,
        "payload": {},
        "correlation_id": None,
        "timestamp": ts.isoformat(),
        "event_id": event_id,
    }


def _make_mock_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestBufferAppendAndCapacity:
    """FR-001 / INV-005: deque append and automatic FIFO eviction."""

    async def test_broadcast_appends_to_buffer(self) -> None:
        """Each broadcast should leave a copy in the replay buffer."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        event = build_event(EventType.JOB_PROGRESS, job_id="job-a")

        await manager.broadcast(event)

        assert manager.buffered_event_count == 1
        assert manager.replay_since(None) == [event]

    async def test_broadcast_evicts_oldest_when_full(self) -> None:
        """Once the buffer reaches capacity, the oldest event is evicted."""
        manager = ConnectionManager(buffer_size=3, ttl_seconds=300)
        events = [build_event(EventType.JOB_PROGRESS, job_id="job-a") for _ in range(5)]

        for event in events:
            await manager.broadcast(event)

        remaining = manager.replay_since(None)
        assert manager.buffered_event_count == 3
        assert [e["event_id"] for e in remaining] == [e["event_id"] for e in events[-3:]]

    async def test_zero_sized_buffer_disables_replay(self) -> None:
        """``buffer_size=0`` disables the replay buffer entirely."""
        manager = ConnectionManager(buffer_size=0, ttl_seconds=300)
        event = build_event(EventType.JOB_PROGRESS, job_id="job-a")

        await manager.broadcast(event)

        assert manager.buffered_event_count == 0
        assert manager.replay_since(None) == []
        assert manager.replay_since("event-00000") == []


class TestReplayFiltering:
    """FR-003 / FR-004: filter by ``Last-Event-ID`` in broadcast order."""

    async def test_replay_returns_events_after_last_event_id(self) -> None:
        """Events strictly after the supplied id are returned in order."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        events = [build_event(EventType.JOB_PROGRESS, job_id="job-a") for _ in range(5)]
        for event in events:
            await manager.broadcast(event)

        replay = manager.replay_since(events[1]["event_id"])

        assert [e["event_id"] for e in replay] == [e["event_id"] for e in events[2:]]

    async def test_replay_without_header_returns_all_fresh(self) -> None:
        """Empty or missing ``Last-Event-ID`` returns every non-expired event."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        events = [build_event(EventType.JOB_PROGRESS, job_id="job-a") for _ in range(3)]
        for event in events:
            await manager.broadcast(event)

        assert manager.replay_since(None) == events
        assert manager.replay_since("") == events

    async def test_replay_with_unknown_event_id_returns_all_fresh(self) -> None:
        """Unknown ids (evicted or never seen) replay the full fresh buffer."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        events = [build_event(EventType.JOB_PROGRESS, job_id="job-a") for _ in range(3)]
        for event in events:
            await manager.broadcast(event)

        replay = manager.replay_since("event-99999")

        assert [e["event_id"] for e in replay] == [e["event_id"] for e in events]

    async def test_replay_with_latest_event_id_returns_empty(self) -> None:
        """Asking for the tail id returns no events (caller is up to date)."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        events = [build_event(EventType.JOB_PROGRESS, job_id="job-a") for _ in range(3)]
        for event in events:
            await manager.broadcast(event)

        assert manager.replay_since(events[-1]["event_id"]) == []

    async def test_replay_empty_buffer_returns_empty_list(self) -> None:
        """A fresh manager replays nothing regardless of the header."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)

        assert manager.replay_since(None) == []
        assert manager.replay_since("event-00000") == []


class TestTtlFiltering:
    """FR-002 / INV-006: events older than TTL are excluded on replay."""

    async def test_expired_events_are_excluded(self) -> None:
        """Events with timestamps older than the TTL are not replayed."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=60)
        now = datetime.now(timezone.utc)
        stale = _make_event("event-00000", timestamp=now - timedelta(seconds=600))
        fresh = _make_event("event-00001", timestamp=now)

        await manager.broadcast(stale)
        await manager.broadcast(fresh)

        replay = manager.replay_since(None)
        assert [e["event_id"] for e in replay] == ["event-00001"]

    async def test_replay_after_expired_anchor_returns_all_fresh(self) -> None:
        """If the anchor id has aged out, replay falls back to fresh events."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=60)
        now = datetime.now(timezone.utc)
        stale = _make_event("event-00000", timestamp=now - timedelta(seconds=600))
        fresh_a = _make_event("event-00001", timestamp=now)
        fresh_b = _make_event("event-00002", timestamp=now)

        await manager.broadcast(stale)
        await manager.broadcast(fresh_a)
        await manager.broadcast(fresh_b)

        # The anchor id was expired; the client receives all fresh events.
        replay = manager.replay_since("event-00000")
        assert [e["event_id"] for e in replay] == ["event-00001", "event-00002"]


class TestBroadcastSideEffects:
    """Broadcast must both fan out AND buffer without dropping either path."""

    async def test_broadcast_buffers_even_with_no_clients(self) -> None:
        """Events broadcast while no client is connected still buffer for later."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        event = build_event(EventType.JOB_PROGRESS, job_id="job-a")

        await manager.broadcast(event)

        assert manager.buffered_event_count == 1
        assert manager.replay_since(None)[0]["event_id"] == event["event_id"]

    async def test_broadcast_buffers_even_when_send_fails(self) -> None:
        """Dead-client send failures do not prevent buffering of the event."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        dead = _make_mock_ws()
        dead.send_json.side_effect = RuntimeError("connection closed")
        await manager.connect(dead)
        event = build_event(EventType.JOB_PROGRESS, job_id="job-a")

        await manager.broadcast(event)

        assert manager.active_connections == 0
        assert manager.replay_since(None)[0]["event_id"] == event["event_id"]


class TestReplayPreservesOrder:
    """FR-004: oldest buffered event first, newest last."""

    async def test_replay_preserves_insertion_order(self) -> None:
        """Replay order matches original broadcast order."""
        manager = ConnectionManager(buffer_size=10, ttl_seconds=300)
        ids = [f"event-{i:05d}" for i in range(5)]
        now = datetime.now(timezone.utc)
        for i, eid in enumerate(ids):
            await manager.broadcast(_make_event(eid, timestamp=now + timedelta(seconds=i)))

        replay = manager.replay_since(None)

        assert [e["event_id"] for e in replay] == ids


class TestSettingsDefaults:
    """Buffer size and TTL default to settings when not passed explicitly."""

    async def test_defaults_are_loaded_from_settings(self) -> None:
        """With no constructor args, settings values are used."""
        manager = ConnectionManager()

        # Default settings: buffer_size=1000, ttl_seconds=300.
        assert manager.replay_buffer_size == 1000
        assert manager.replay_ttl_seconds == 300
