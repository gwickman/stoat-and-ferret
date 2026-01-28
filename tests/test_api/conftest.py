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
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for API requests.

    The TestClient handles lifespan events automatically.

    Args:
        app: FastAPI application fixture.

    Yields:
        Test client for making HTTP requests.
    """
    with TestClient(app) as c:
        yield c
