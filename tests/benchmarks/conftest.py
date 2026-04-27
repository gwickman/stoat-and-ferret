"""Shared fixtures for the BL-288 performance benchmark suite.

The benchmarks intentionally avoid mocks (LRN-250 / NFR-003): they hit
the live FastAPI app via :class:`fastapi.testclient.TestClient` and the
live :class:`ConnectionManager` directly. Both fixtures are session-
scoped because the seed-and-replay setup is the dominant cost — re-
seeding 100 projects per test would dominate the wall clock.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.batch_repository import InMemoryBatchRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository


@pytest.fixture(scope="session")
def benchmark_settings() -> Settings:
    """Return a Settings instance with testing_mode enabled.

    The seed endpoint is gated by ``testing_mode``; the seeded_100_projects
    fixture writes via that endpoint.
    """
    return Settings(testing_mode=True, seed_endpoint=True)


@pytest.fixture(scope="session")
def benchmark_client(benchmark_settings: Settings) -> Generator[TestClient, None, None]:
    """Build a TestClient against the live FastAPI app with in-memory repos.

    Session-scoped so the seed step runs once for the whole benchmark
    session. The injected repositories bypass the SQLite lifespan path
    (which would touch a real database file) but every API call still
    flows through the real FastAPI router stack so the latency numbers
    are representative.
    """
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        timeline_repository=AsyncInMemoryTimelineRepository(),
        version_repository=AsyncInMemoryVersionRepository(),
        batch_repository=InMemoryBatchRepository(),
        proxy_repository=InMemoryProxyRepository(),
        render_repository=InMemoryRenderRepository(),
        job_queue=InMemoryJobQueue(),
    )
    with TestClient(app) as client:
        # Override the cached settings on app.state so the testing-mode
        # guard accepts the seed endpoint without requiring a real env
        # var. Must run after the lifespan startup (which always sets
        # ``_settings = get_settings()`` before yielding).
        app.state._settings = benchmark_settings
        yield client


@pytest.fixture(scope="session")
def seeded_100_projects(benchmark_client: TestClient) -> list[str]:
    """Seed 100 distinct projects via POST /api/v1/testing/seed.

    Returns the list of fixture ids so individual benchmarks can
    selectively exercise a project lookup if needed. The fixture is
    session-scoped — repeated benchmarks share the same seeded state.
    """
    fixture_ids: list[str] = []
    for i in range(100):
        response = benchmark_client.post(
            "/api/v1/testing/seed",
            json={
                "fixture_type": "project",
                "name": f"benchmark_{i:03d}",
                "data": {},
            },
        )
        response.raise_for_status()
        fixture_ids.append(response.json()["fixture_id"])
    return fixture_ids


@pytest.fixture(scope="session")
def replay_buffer_1000_events() -> tuple[ConnectionManager, list[str]]:
    """Construct a ConnectionManager and pre-fill its replay buffer.

    Returns a tuple of (manager, event_ids) so benchmarks can pick a
    middle event id and exercise the typical "client reconnects after a
    short disconnect" code path.

    The buffer is populated synchronously by appending directly to the
    underlying deque so the fixture stays cheap and deterministic — the
    replay_since() method under benchmark only reads from that deque.
    """
    manager = ConnectionManager(buffer_size=1000, ttl_seconds=86_400)
    event_ids: list[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for i in range(1000):
        event_id = f"event_{i:04d}"
        event_ids.append(event_id)
        message: dict[str, Any] = {
            "event_id": event_id,
            "type": "benchmark.event",
            "timestamp": now_iso,
            "sequence": i,
        }
        manager._replay_buffer.append(message)
    return manager, event_ids
