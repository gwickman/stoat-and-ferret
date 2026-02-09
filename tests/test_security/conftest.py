"""Security test fixtures with full DI wiring."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


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
    """Test client for security API requests."""
    with TestClient(app) as c:
        yield c
