"""Integration tests for dependency injection wiring.

Verifies that create_app() parameter injection works end-to-end:
InMemory repositories injected via create_app() are used by API endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from tests.test_repository_contract import make_test_video


@pytest.mark.api
async def test_injected_video_repo_used_by_endpoint() -> None:
    """API endpoint reads from injected InMemory video repository."""
    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    # Seed a video into the in-memory repo
    video = make_test_video()
    await video_repo.add(video)

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/videos")
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 1
        assert data["videos"][0]["id"] == video.id


@pytest.mark.api
async def test_injected_project_repo_used_by_endpoint() -> None:
    """API endpoint reads from injected InMemory project repository."""
    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
    )

    with TestClient(app) as client:
        # Create a project via API
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "DI Test Project",
                "output_width": 1920,
                "output_height": 1080,
                "output_fps": 24.0,
            },
        )
        assert response.status_code == 201
        project_id = response.json()["id"]

        # Verify project exists in the injected repo
        project = await project_repo.get(project_id)
        assert project is not None
        assert project.name == "DI Test Project"


@pytest.mark.api
def test_create_app_no_params_preserves_production_behavior() -> None:
    """create_app() with no params does not set _deps_injected flag."""
    app = create_app()
    assert not getattr(app.state, "_deps_injected", False)
    assert getattr(app.state, "video_repository", None) is None


@pytest.mark.api
def test_create_app_with_repos_sets_injected_flag() -> None:
    """create_app() with repos sets _deps_injected flag on app.state."""
    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
    )
    assert app.state._deps_injected is True
    assert app.state.video_repository is video_repo
    assert app.state.project_repository is project_repo
    assert app.state.clip_repository is clip_repo


@pytest.mark.api
def test_zero_dependency_overrides_in_conftest(client: TestClient) -> None:
    """Verify no dependency_overrides are set on the test app."""
    assert len(client.app.dependency_overrides) == 0  # type: ignore[union-attr]
