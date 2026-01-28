"""Shared fixtures for API tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings, get_settings
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the temporary test database file.
    """
    return tmp_path / "test.db"


@pytest.fixture
def test_settings(test_db_path: Path) -> Settings:
    """Create test settings with temporary database.

    Args:
        test_db_path: Path to temporary database.

    Returns:
        Settings configured for testing.
    """
    return Settings(
        api_host="127.0.0.1",
        api_port=8000,
        database_path=str(test_db_path),
    )


@pytest.fixture
def app(test_settings: Settings, monkeypatch: Any) -> FastAPI:
    """Create test application with test settings.

    Patches get_settings to return test configuration.

    Args:
        test_settings: Test settings fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        Configured FastAPI application for testing.
    """
    # Clear the cached settings
    get_settings.cache_clear()
    # Patch to return test settings
    monkeypatch.setattr("stoat_ferret.api.settings.get_settings", lambda: test_settings)
    monkeypatch.setattr("stoat_ferret.api.app.get_settings", lambda: test_settings)
    return create_app()


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
def client(
    app: FastAPI,
    video_repository: AsyncInMemoryVideoRepository,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> Generator[TestClient, None, None]:
    """Create test client for API requests.

    The TestClient handles lifespan events automatically.
    Overrides all repository dependencies with in-memory implementations.

    Args:
        app: FastAPI application fixture.
        video_repository: In-memory video repository for testing.
        project_repository: In-memory project repository for testing.
        clip_repository: In-memory clip repository for testing.

    Yields:
        Test client for making HTTP requests.
    """
    from stoat_ferret.api.routers.projects import (
        get_clip_repository,
        get_project_repository,
        get_video_repository,
    )
    from stoat_ferret.api.routers.videos import get_repository

    app.dependency_overrides[get_repository] = lambda: video_repository
    app.dependency_overrides[get_project_repository] = lambda: project_repository
    app.dependency_overrides[get_clip_repository] = lambda: clip_repository
    app.dependency_overrides[get_video_repository] = lambda: video_repository

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
