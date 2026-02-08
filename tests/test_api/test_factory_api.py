"""Integration tests for fixture factory create_via_api() and ApiFactory."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from tests.factories import ProjectFactory, make_test_video

# ---------------------------------------------------------------------------
# ProjectFactory.create_via_api() integration tests
# ---------------------------------------------------------------------------


class TestProjectFactoryCreateViaApi:
    """Integration tests for create_via_api() (full HTTP path)."""

    @pytest.mark.api
    def test_create_project_via_api(self, client: TestClient) -> None:
        """create_via_api() creates a project through the API."""
        result = ProjectFactory().with_name("API Project").create_via_api(client)
        assert result["project"]["name"] == "API Project"
        assert result["project"]["output_width"] == 1920
        assert result["clips"] == []

    @pytest.mark.api
    def test_create_project_custom_output_via_api(self, client: TestClient) -> None:
        """create_via_api() passes custom output settings."""
        result = (
            ProjectFactory()
            .with_name("4K")
            .with_output(width=3840, height=2160, fps=60)
            .create_via_api(client)
        )
        assert result["project"]["output_width"] == 3840
        assert result["project"]["output_height"] == 2160
        assert result["project"]["output_fps"] == 60

    @pytest.mark.api
    async def test_create_project_with_clip_via_api(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        """create_via_api() creates project and clip through the API."""
        video = make_test_video()
        await video_repository.add(video)

        result = (
            ProjectFactory()
            .with_name("With Clip")
            .with_clip(source_video_id=video.id, in_point=0, out_point=50)
            .create_via_api(client)
        )
        assert result["project"]["name"] == "With Clip"
        assert len(result["clips"]) == 1
        assert result["clips"][0]["source_video_id"] == video.id
        assert result["clips"][0]["in_point"] == 0
        assert result["clips"][0]["out_point"] == 50


# ---------------------------------------------------------------------------
# ApiFactory integration tests
# ---------------------------------------------------------------------------


class TestApiFactory:
    """Integration tests for the ApiFactory fixture."""

    @pytest.mark.api
    def test_api_factory_creates_project(
        self,
        api_factory: Any,  # noqa: ANN401
    ) -> None:
        """ApiFactory creates a project via the API."""
        result = api_factory.project().with_name("Factory Project").create()
        assert result["project"]["name"] == "Factory Project"

    @pytest.mark.api
    async def test_api_factory_creates_project_with_clip(
        self,
        api_factory: Any,  # noqa: ANN401
    ) -> None:
        """ApiFactory auto-seeds video and creates clip via the API."""
        builder = api_factory.project().with_name("With Clip")
        await builder.with_clip(in_point=0, out_point=75)
        result = builder.create()

        assert result["project"]["name"] == "With Clip"
        assert len(result["clips"]) == 1
        assert result["clips"][0]["in_point"] == 0
        assert result["clips"][0]["out_point"] == 75
