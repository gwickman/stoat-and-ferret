"""Tests for FastAPI application factory and lifespan."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app


def test_create_app_returns_fastapi_instance() -> None:
    """Application factory returns a FastAPI instance."""
    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_has_correct_title() -> None:
    """Application has expected title."""
    app = create_app()
    assert app.title == "stoat-and-ferret"


def test_create_app_has_correct_version() -> None:
    """Application has expected version."""
    app = create_app()
    assert app.version == "0.3.0"


def test_create_app_has_lifespan() -> None:
    """Application has lifespan manager configured."""
    app = create_app()
    assert app.router.lifespan_context is not None


@pytest.mark.api
def test_app_starts_with_test_client(client: TestClient) -> None:
    """Application can be started via TestClient.

    This test verifies that the lifespan events (startup/shutdown)
    execute without error when using the test client.
    """
    # If we get here, the app started successfully
    assert client is not None


@pytest.mark.api
def test_openapi_docs_available(client: TestClient) -> None:
    """OpenAPI documentation is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "stoat-and-ferret"
    assert data["info"]["version"] == "0.3.0"


@pytest.mark.api
def test_injected_repositories_in_state(client: TestClient) -> None:
    """Injected repositories are stored in app.state after startup."""
    # The client fixture uses create_app() with injected in-memory repositories
    assert hasattr(client.app.state, "video_repository")
    assert client.app.state.video_repository is not None
    assert hasattr(client.app.state, "project_repository")
    assert client.app.state.project_repository is not None
    assert hasattr(client.app.state, "clip_repository")
    assert client.app.state.clip_repository is not None
