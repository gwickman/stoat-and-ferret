"""Integration tests for the thumbnail API endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from tests.factories import make_test_video


@pytest.mark.api
async def test_returns_thumbnail_for_video_with_thumbnail(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
    tmp_path: Path,
) -> None:
    """Returns the thumbnail image when it exists on disk."""
    thumb_file = tmp_path / "thumb.jpg"
    thumb_file.write_bytes(b"\xff\xd8\xff\xe0test-thumbnail-data")

    video = make_test_video(thumbnail_path=str(thumb_file))
    await video_repository.add(video)

    response = client.get(f"/api/v1/videos/{video.id}/thumbnail")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"\xff\xd8\xff\xe0test-thumbnail-data"


@pytest.mark.api
async def test_returns_placeholder_for_video_without_thumbnail(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Returns placeholder when video has no thumbnail_path."""
    video = make_test_video(thumbnail_path=None)
    await video_repository.add(video)

    response = client.get(f"/api/v1/videos/{video.id}/thumbnail")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert len(response.content) > 0


@pytest.mark.api
async def test_returns_placeholder_for_missing_thumbnail_file(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Returns placeholder when thumbnail_path points to missing file."""
    video = make_test_video(thumbnail_path="/nonexistent/thumb.jpg")
    await video_repository.add(video)

    response = client.get(f"/api/v1/videos/{video.id}/thumbnail")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


@pytest.mark.api
def test_returns_404_for_unknown_video(
    client: TestClient,
) -> None:
    """Returns 404 when video ID doesn't exist."""
    response = client.get("/api/v1/videos/nonexistent-id/thumbnail")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_thumbnail_content_type_is_jpeg(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
    tmp_path: Path,
) -> None:
    """Thumbnail response Content-Type is image/jpeg."""
    thumb_file = tmp_path / "thumb.jpg"
    thumb_file.write_bytes(b"\xff\xd8\xff\xe0jpeg-data")

    video = make_test_video(thumbnail_path=str(thumb_file))
    await video_repository.add(video)

    response = client.get(f"/api/v1/videos/{video.id}/thumbnail")

    assert response.headers["content-type"] == "image/jpeg"
