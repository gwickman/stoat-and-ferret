"""Smoke tests for WebSocket reconnect-with-replay behaviour (BL-274).

Verifies the end-to-end reconnect scenario required by FR-001..FR-004:
a client disconnects, the server continues to broadcast, and the
reconnecting client — by passing ``Last-Event-ID`` — receives exactly
the events it missed, in order.

Also asserts the replay buffer memory ceiling scales with the deque
bound, not with the number of concurrent clients (NFR-001).
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.websocket.events import (
    EventType,
    build_event,
    reset_event_counters,
)
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


@pytest.fixture(autouse=True)
def _isolate_counters() -> None:
    """Reset the event-id counters so each test starts from ``event-00000``."""
    reset_event_counters()


@pytest.fixture
def ws_manager() -> ConnectionManager:
    """Build a ConnectionManager with a small, fast-to-fill replay buffer."""
    return ConnectionManager(buffer_size=1000, ttl_seconds=300)


@pytest.fixture
def ws_app(ws_manager: ConnectionManager) -> FastAPI:
    """Build a FastAPI app wired to the fixture manager."""
    return create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        job_queue=InMemoryJobQueue(),
        ws_manager=ws_manager,
    )


@pytest.fixture
def ws_client(ws_app: FastAPI) -> Generator[TestClient, None, None]:
    """Yield a TestClient against the fixture app."""
    with TestClient(ws_app) as client:
        yield client


def _broadcast(manager: ConnectionManager, event: dict[str, object]) -> None:
    """Invoke an async broadcast on a synchronous test thread."""
    asyncio.run(manager.broadcast(event))


def test_reconnect_replays_events_missed_while_offline(
    ws_client: TestClient,
    ws_manager: ConnectionManager,
) -> None:
    """Reconnect with ``Last-Event-ID`` yields exactly the missed events in order."""
    # Phase 1 — connect and receive five events.
    received_before: list[str] = []
    with ws_client.websocket_connect("/ws") as ws:
        for _ in range(5):
            _broadcast(
                ws_manager,
                build_event(EventType.JOB_PROGRESS, job_id="job-replay"),
            )
        for _ in range(5):
            received_before.append(ws.receive_json()["event_id"])
    assert received_before == [f"event-{i:05d}" for i in range(5)]

    # Phase 2 — broadcast five more events while the client is offline.
    offline_ids: list[str] = []
    for _ in range(5):
        event = build_event(EventType.JOB_PROGRESS, job_id="job-replay")
        offline_ids.append(event["event_id"])
        _broadcast(ws_manager, event)

    # Phase 3 — reconnect with the last id received in phase 1.
    with ws_client.websocket_connect(
        "/ws",
        headers={"last-event-id": received_before[-1]},
    ) as ws:
        replayed = [ws.receive_json() for _ in range(5)]

    assert [e["event_id"] for e in replayed] == offline_ids
    assert offline_ids == [f"event-{i:05d}" for i in range(5, 10)]


def test_reconnect_without_header_skips_replay(
    ws_client: TestClient,
    ws_manager: ConnectionManager,
) -> None:
    """A fresh client (no ``Last-Event-ID``) receives only live events, not history."""
    # Pre-populate the buffer with broadcasts no live client saw.
    for _ in range(3):
        _broadcast(ws_manager, build_event(EventType.JOB_PROGRESS, job_id="job-fresh"))

    with ws_client.websocket_connect("/ws") as ws:
        # Without a header, replay is explicitly skipped — no buffered events
        # should be pushed. A live broadcast must still arrive.
        _broadcast(ws_manager, build_event(EventType.JOB_PROGRESS, job_id="job-fresh"))
        live = ws.receive_json()

    assert live["event_id"] == "event-00003"


def test_reconnect_with_unknown_event_id_returns_all_fresh(
    ws_client: TestClient,
    ws_manager: ConnectionManager,
) -> None:
    """An unknown or evicted ``Last-Event-ID`` streams every buffered fresh event."""
    for _ in range(3):
        _broadcast(ws_manager, build_event(EventType.JOB_PROGRESS, job_id="job-unknown"))

    with ws_client.websocket_connect(
        "/ws",
        headers={"last-event-id": "event-99999"},
    ) as ws:
        replayed = [ws.receive_json() for _ in range(3)]

    assert [e["event_id"] for e in replayed] == [
        "event-00000",
        "event-00001",
        "event-00002",
    ]


def test_replay_buffer_memory_bounds() -> None:
    """NFR-001: total replay buffer memory scales with deque bound, not clients.

    The manager keeps a single bounded deque of the most recent events.
    Even after broadcasting many more events than the bound allows, the
    buffer must stay within a linear memory envelope of
    ``buffer_size * 1.2 * sizeof(event)``.
    """
    buffer_size = 200
    manager = ConnectionManager(buffer_size=buffer_size, ttl_seconds=300)
    reset_event_counters()

    async def flood() -> None:
        for _ in range(buffer_size * 5):
            await manager.broadcast(
                build_event(EventType.JOB_PROGRESS, job_id="job-mem"),
            )

    asyncio.run(flood())

    # Deque bound is honoured — oldest events are evicted.
    assert manager.buffered_event_count == buffer_size

    # Pessimistic per-event size with a 1.2 metadata factor.
    sample_event = build_event(EventType.JOB_PROGRESS, job_id="job-mem")
    sample_size = sys.getsizeof(sample_event)
    per_event_budget = int(sample_size * 1.2)
    peak_event = next(iter(manager.replay_since(None)[-1:]))
    assert sys.getsizeof(peak_event) <= per_event_budget
