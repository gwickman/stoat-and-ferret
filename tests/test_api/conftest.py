"""Shared fixtures for API tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """Create in-memory video repository for testing.

    Returns:
        Empty in-memory video repository.
    """
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def project_repository() -> AsyncInMemoryProjectRepository:
    """Create in-memory project repository for testing.

    Returns:
        Empty in-memory project repository.
    """
    return AsyncInMemoryProjectRepository()


@pytest.fixture
def clip_repository() -> AsyncInMemoryClipRepository:
    """Create in-memory clip repository for testing.

    Returns:
        Empty in-memory clip repository.
    """
    return AsyncInMemoryClipRepository()


@pytest.fixture
def app(
    video_repository: AsyncInMemoryVideoRepository,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> FastAPI:
    """Create test application with injected in-memory repositories.

    Uses create_app() parameter injection instead of dependency_overrides.

    Args:
        video_repository: In-memory video repository for testing.
        project_repository: In-memory project repository for testing.
        clip_repository: In-memory clip repository for testing.

    Returns:
        Configured FastAPI application for testing.
    """
    return create_app(
        video_repository=video_repository,
        project_repository=project_repository,
        clip_repository=clip_repository,
    )


@pytest.fixture
def client(
    app: FastAPI,
) -> Generator[TestClient, None, None]:
    """Create test client for API requests.

    The TestClient handles lifespan events automatically.
    Repositories are injected via create_app() parameters.

    Args:
        app: FastAPI application fixture.

    Yields:
        Test client for making HTTP requests.
    """
    with TestClient(app) as c:
        yield c
