"""Black box test fixtures with full DI wiring.

All fixtures inject in-memory test doubles via create_app() so tests
exercise the complete REST API stack without needing FFmpeg or a database.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from tests.factories import make_test_video


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """Empty in-memory video repository."""
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def project_repository() -> AsyncInMemoryProjectRepository:
    """Empty in-memory project repository."""
    return AsyncInMemoryProjectRepository()


@pytest.fixture
def clip_repository() -> AsyncInMemoryClipRepository:
    """Empty in-memory clip repository."""
    return AsyncInMemoryClipRepository()


@pytest.fixture
def job_queue(video_repository: AsyncInMemoryVideoRepository) -> InMemoryJobQueue:
    """In-memory job queue with scan handler registered."""
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repository))
    return queue


@pytest.fixture
def app(
    video_repository: AsyncInMemoryVideoRepository,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    job_queue: InMemoryJobQueue,
) -> FastAPI:
    """Create app with injected in-memory test doubles."""
    return create_app(
        video_repository=video_repository,
        project_repository=project_repository,
        clip_repository=clip_repository,
        job_queue=job_queue,
    )


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Test client for black box API requests."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def seeded_video(
    video_repository: AsyncInMemoryVideoRepository,
) -> dict[str, Any]:
    """Seed a single video into the repository and return its data.

    Returns:
        Dict with video fields (id, path, duration_frames, etc.).
    """
    video = make_test_video()
    await video_repository.add(video)
    return {
        "id": video.id,
        "path": video.path,
        "duration_frames": video.duration_frames,
    }


def create_project_via_api(
    client: TestClient, name: str = "Test Project", **kwargs: Any
) -> dict[str, Any]:
    """Create a project through the REST API.

    Args:
        client: TestClient instance.
        name: Project name.
        **kwargs: Additional project fields (output_width, output_height, output_fps).

    Returns:
        Project response dict.
    """
    payload: dict[str, Any] = {"name": name, **kwargs}
    resp = client.post("/api/v1/projects", json=payload)
    assert resp.status_code == 201, f"Failed to create project: {resp.text}"
    return resp.json()


def add_clip_via_api(
    client: TestClient,
    project_id: str,
    source_video_id: str,
    in_point: int = 0,
    out_point: int = 100,
    timeline_position: int = 0,
) -> dict[str, Any]:
    """Add a clip to a project through the REST API.

    Args:
        client: TestClient instance.
        project_id: Target project ID.
        source_video_id: Source video ID.
        in_point: Clip start frame.
        out_point: Clip end frame.
        timeline_position: Position on timeline.

    Returns:
        Clip response dict.
    """
    payload = {
        "source_video_id": source_video_id,
        "in_point": in_point,
        "out_point": out_point,
        "timeline_position": timeline_position,
    }
    resp = client.post(f"/api/v1/projects/{project_id}/clips", json=payload)
    assert resp.status_code == 201, f"Failed to create clip: {resp.text}"
    return resp.json()
