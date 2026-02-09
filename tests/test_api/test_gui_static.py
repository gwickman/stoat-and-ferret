"""Tests for GUI static file serving via FastAPI."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue


@pytest.fixture
def gui_dist_dir(tmp_path: Path) -> Path:
    """Create a minimal gui/dist directory with index.html.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the fake gui/dist directory.
    """
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><html><body>stoat-ferret gui</body></html>")
    assets = dist / "assets"
    assets.mkdir()
    (assets / "index.js").write_text("console.log('hello')")
    return dist


@pytest.fixture
def client_with_gui(gui_dist_dir: Path) -> TestClient:
    """Create a test client with GUI static files mounted.

    Args:
        gui_dist_dir: Path to fake dist directory.

    Returns:
        Test client with GUI mount.
    """
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        job_queue=InMemoryJobQueue(),
        gui_static_path=gui_dist_dir,
    )
    with TestClient(app) as c:
        yield c


@pytest.mark.api
class TestGuiStaticServing:
    """Tests for the /gui static file mount."""

    def test_gui_serves_index_html(self, client_with_gui: TestClient) -> None:
        """GET /gui/ returns index.html content."""
        response = client_with_gui.get("/gui/")
        assert response.status_code == 200
        assert "stoat-ferret gui" in response.text

    def test_gui_serves_static_assets(self, client_with_gui: TestClient) -> None:
        """GET /gui/assets/index.js returns the JS file."""
        response = client_with_gui.get("/gui/assets/index.js")
        assert response.status_code == 200
        assert "hello" in response.text

    def test_api_routes_still_work(self, client_with_gui: TestClient) -> None:
        """API routes remain accessible after GUI mount."""
        response = client_with_gui.get("/health/live")
        assert response.status_code == 200

    def test_gui_not_mounted_when_path_missing(self) -> None:
        """GUI is not mounted when gui_static_path does not exist."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            job_queue=InMemoryJobQueue(),
            gui_static_path="/nonexistent/path",
        )
        with TestClient(app) as c:
            response = c.get("/gui/")
            assert response.status_code == 404

    def test_gui_not_mounted_when_path_none(self, client: TestClient) -> None:
        """GUI is not mounted when gui_static_path is None (default)."""
        response = client.get("/gui/")
        assert response.status_code == 404
