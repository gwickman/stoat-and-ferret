"""Tests for SPA routing fallback on GUI sub-paths."""

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
    """Create a minimal gui/dist directory with index.html and a test asset.

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
    (assets / "main.js").write_text("console.log('app')")
    return dist


@pytest.fixture
def spa_client(gui_dist_dir: Path) -> TestClient:
    """Create a test client with SPA routing enabled.

    Args:
        gui_dist_dir: Path to fake dist directory.

    Returns:
        Test client with SPA routes.
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
class TestSpaRoutingFallback:
    """Tests for SPA fallback serving index.html on GUI sub-paths."""

    def test_gui_library_returns_index_html(self, spa_client: TestClient) -> None:
        """GET /gui/library returns 200 with index.html content."""
        response = spa_client.get("/gui/library")
        assert response.status_code == 200
        assert "stoat-ferret gui" in response.text

    def test_gui_projects_returns_index_html(self, spa_client: TestClient) -> None:
        """GET /gui/projects returns 200 with index.html content."""
        response = spa_client.get("/gui/projects")
        assert response.status_code == 200
        assert "stoat-ferret gui" in response.text

    def test_gui_arbitrary_subpath_returns_index_html(self, spa_client: TestClient) -> None:
        """GET /gui/any-sub-path returns SPA content."""
        response = spa_client.get("/gui/any-sub-path")
        assert response.status_code == 200
        assert "stoat-ferret gui" in response.text

    def test_gui_nested_subpath_returns_index_html(self, spa_client: TestClient) -> None:
        """GET /gui/some/nested/path returns SPA content."""
        response = spa_client.get("/gui/some/nested/path")
        assert response.status_code == 200
        assert "stoat-ferret gui" in response.text


@pytest.mark.api
class TestStaticFileServing:
    """Tests for static file serving through the catch-all route."""

    def test_existing_asset_returns_file_content(self, spa_client: TestClient) -> None:
        """GET /gui/assets/main.js returns the JavaScript file, not index.html."""
        response = spa_client.get("/gui/assets/main.js")
        assert response.status_code == 200
        assert "console.log('app')" in response.text
        assert "stoat-ferret gui" not in response.text


@pytest.mark.api
class TestBareGuiPath:
    """Tests for the bare /gui path."""

    def test_bare_gui_returns_index_html(self, spa_client: TestClient) -> None:
        """GET /gui returns 200 with index.html content."""
        response = spa_client.get("/gui")
        assert response.status_code == 200
        assert "stoat-ferret gui" in response.text


@pytest.mark.api
class TestConditionalActivation:
    """Tests for conditional activation of SPA routes."""

    def test_no_routes_when_gui_dist_missing(self) -> None:
        """Without gui/dist/, no /gui/* routes are registered."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            job_queue=InMemoryJobQueue(),
            gui_static_path="/nonexistent/path",
        )
        with TestClient(app) as c:
            response = c.get("/gui/library")
            assert response.status_code == 404

    def test_no_routes_when_gui_path_none(self, client: TestClient) -> None:
        """Without gui_static_path, no /gui/* routes are registered."""
        response = client.get("/gui/library")
        assert response.status_code == 404


@pytest.mark.api
class TestApiRoutePreservation:
    """Tests that API routes are not affected by SPA routing."""

    def test_health_endpoint_still_works(self, spa_client: TestClient) -> None:
        """API routes remain accessible with SPA routing enabled."""
        response = spa_client.get("/health/live")
        assert response.status_code == 200
