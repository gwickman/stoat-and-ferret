"""Tests for video endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from tests.test_repository_contract import make_test_video


@pytest.mark.api
def test_list_videos_empty(client: TestClient) -> None:
    """List returns empty when no videos."""
    response = client.get("/api/v1/videos")
    assert response.status_code == 200
    data = response.json()
    assert data["videos"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.api
async def test_list_videos_with_data(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """List returns videos when present."""
    video = make_test_video()
    await video_repository.add(video)

    response = client.get("/api/v1/videos")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["id"] == video.id
    assert data["total"] == 1


@pytest.mark.api
async def test_list_videos_respects_limit(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """List respects limit parameter."""
    for _ in range(5):
        await video_repository.add(make_test_video())

    response = client.get("/api/v1/videos?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 3
    assert data["limit"] == 3


@pytest.mark.api
async def test_list_videos_respects_offset(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """List respects offset parameter."""
    for _ in range(5):
        await video_repository.add(make_test_video())

    response = client.get("/api/v1/videos?offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 3
    assert data["offset"] == 2


@pytest.mark.api
def test_list_videos_invalid_limit(client: TestClient) -> None:
    """List returns 422 for invalid limit."""
    response = client.get("/api/v1/videos?limit=0")
    assert response.status_code == 422

    response = client.get("/api/v1/videos?limit=101")
    assert response.status_code == 422


@pytest.mark.api
def test_list_videos_invalid_offset(client: TestClient) -> None:
    """List returns 422 for invalid offset."""
    response = client.get("/api/v1/videos?offset=-1")
    assert response.status_code == 422


@pytest.mark.api
def test_get_video_not_found(client: TestClient) -> None:
    """Get returns 404 for unknown ID."""
    response = client.get("/api/v1/videos/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"
    assert "nonexistent" in data["detail"]["message"]


@pytest.mark.api
async def test_get_video_found(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Get returns video when found."""
    video = make_test_video()
    await video_repository.add(video)

    response = client.get(f"/api/v1/videos/{video.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == video.id
    assert data["path"] == video.path
    assert data["filename"] == video.filename
    assert data["duration_frames"] == video.duration_frames
    assert data["width"] == video.width
    assert data["height"] == video.height
    assert data["video_codec"] == video.video_codec
