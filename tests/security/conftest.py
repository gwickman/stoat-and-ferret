"""Fixtures for the Phase 6 security audit probe suite (BL-286).

Reuses the same in-memory test doubles wired through ``create_app`` that the
existing security tests rely on so the audit probes exercise live FastAPI
routes without depending on a running server. ``testing_mode`` defaults to
``False`` here so the ``/api/v1/testing/seed`` guard is exercised by default.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.api.settings import Settings
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """Empty in-memory video repository for audit probes."""
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def project_repository() -> AsyncInMemoryProjectRepository:
    """Empty in-memory project repository for audit probes."""
    return AsyncInMemoryProjectRepository()


@pytest.fixture
def clip_repository() -> AsyncInMemoryClipRepository:
    """Empty in-memory clip repository for audit probes."""
    return AsyncInMemoryClipRepository()


@pytest.fixture
def job_queue(video_repository: AsyncInMemoryVideoRepository) -> InMemoryJobQueue:
    """In-memory job queue with the scan handler registered."""
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repository))
    return queue


@pytest.fixture
def audit_settings() -> Settings:
    """Settings with ``testing_mode`` disabled (production posture)."""
    return Settings(testing_mode=False)


@pytest.fixture
def app(
    video_repository: AsyncInMemoryVideoRepository,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    job_queue: InMemoryJobQueue,
) -> FastAPI:
    """App with injected in-memory test doubles."""
    return create_app(
        video_repository=video_repository,
        project_repository=project_repository,
        clip_repository=clip_repository,
        job_queue=job_queue,
    )


@pytest.fixture
def client(app: FastAPI, audit_settings: Settings) -> Generator[TestClient, None, None]:
    """Test client for security audit probes.

    The lifespan resets ``app.state._settings`` to ``get_settings()`` on
    startup, so the production-posture override has to land *after* the
    TestClient context enters.
    """
    with TestClient(app) as c:
        app.state._settings = audit_settings
        yield c
