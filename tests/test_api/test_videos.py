"""Tests for video endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.ffmpeg.probe import VideoMetadata
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


@pytest.mark.api
async def test_search_finds_by_filename(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Search finds videos by filename."""
    video = make_test_video(filename="vacation_beach.mp4")
    await video_repository.add(video)

    response = client.get("/api/v1/videos/search?q=beach")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["filename"] == "vacation_beach.mp4"
    assert data["query"] == "beach"


@pytest.mark.api
async def test_search_finds_by_path(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Search finds videos by path."""
    video = make_test_video(path="/videos/summer/clip.mp4", filename="clip.mp4")
    await video_repository.add(video)

    response = client.get("/api/v1/videos/search?q=summer")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["path"] == "/videos/summer/clip.mp4"
    assert data["query"] == "summer"


@pytest.mark.api
def test_search_no_results(client: TestClient) -> None:
    """Search returns empty for no matches."""
    response = client.get("/api/v1/videos/search?q=nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["videos"] == []
    assert data["total"] == 0
    assert data["query"] == "nonexistent"


@pytest.mark.api
def test_search_requires_query(client: TestClient) -> None:
    """Search requires query parameter."""
    response = client.get("/api/v1/videos/search")
    assert response.status_code == 422


@pytest.mark.api
def test_search_query_min_length(client: TestClient) -> None:
    """Search query must be at least 1 character."""
    response = client.get("/api/v1/videos/search?q=")
    assert response.status_code == 422


@pytest.mark.api
async def test_search_respects_limit(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Search respects limit parameter."""
    for i in range(5):
        await video_repository.add(make_test_video(filename=f"test_video_{i}.mp4"))

    response = client.get("/api/v1/videos/search?q=test_video&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 3
    assert data["total"] == 3


# --- Scan endpoint tests ---


def _make_mock_metadata() -> VideoMetadata:
    """Create mock video metadata for testing."""
    return VideoMetadata(
        duration_seconds=10.0,
        width=1920,
        height=1080,
        frame_rate_numerator=24,
        frame_rate_denominator=1,
        video_codec="h264",
        audio_codec="aac",
        file_size=1000000,
    )


@pytest.mark.api
def test_scan_invalid_path(client: TestClient) -> None:
    """Scan returns 400 for invalid path."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": "/nonexistent/directory"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "INVALID_PATH"


@pytest.mark.api
def test_scan_empty_directory(client: TestClient, tmp_path: Path) -> None:
    """Scan of empty directory returns zeros."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scanned"] == 0
    assert data["new"] == 0
    assert data["updated"] == 0
    assert data["skipped"] == 0
    assert data["errors"] == []


@pytest.mark.api
def test_scan_finds_video_files(client: TestClient, tmp_path: Path) -> None:
    """Scan finds and adds video files."""
    # Create test video files
    (tmp_path / "video1.mp4").touch()
    (tmp_path / "video2.mkv").touch()
    (tmp_path / "not_video.txt").touch()

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        return_value=mock_metadata,
    ):
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["scanned"] == 2
    assert data["new"] == 2
    assert data["updated"] == 0
    assert data["skipped"] == 0
    assert data["errors"] == []


@pytest.mark.api
def test_scan_recursive(client: TestClient, tmp_path: Path) -> None:
    """Scan recursively finds videos in subdirectories."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (tmp_path / "video1.mp4").touch()
    (subdir / "video2.mp4").touch()

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        return_value=mock_metadata,
    ):
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path), "recursive": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["scanned"] == 2
    assert data["new"] == 2


@pytest.mark.api
def test_scan_non_recursive(client: TestClient, tmp_path: Path) -> None:
    """Scan with recursive=False ignores subdirectories."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (tmp_path / "video1.mp4").touch()
    (subdir / "video2.mp4").touch()

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        return_value=mock_metadata,
    ):
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path), "recursive": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["scanned"] == 1
    assert data["new"] == 1


@pytest.mark.api
async def test_scan_updates_existing_videos(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
    tmp_path: Path,
) -> None:
    """Scan updates existing videos in repository."""
    video_path = tmp_path / "existing.mp4"
    video_path.touch()

    # Add existing video to repository
    existing_video = make_test_video(
        path=str(video_path.absolute()),
        filename="existing.mp4",
    )
    await video_repository.add(existing_video)

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        return_value=mock_metadata,
    ):
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["scanned"] == 1
    assert data["new"] == 0
    assert data["updated"] == 1


@pytest.mark.api
def test_scan_handles_errors_gracefully(client: TestClient, tmp_path: Path) -> None:
    """Scan continues even if individual files fail."""
    (tmp_path / "good.mp4").touch()
    (tmp_path / "bad.mp4").touch()

    mock_metadata = _make_mock_metadata()
    call_count = 0

    def mock_probe(path: str) -> VideoMetadata:
        nonlocal call_count
        call_count += 1
        if "bad" in path:
            raise ValueError("Probe failed")
        return mock_metadata

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        side_effect=mock_probe,
    ):
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["scanned"] == 2
    assert data["new"] == 1
    assert len(data["errors"]) == 1
    assert "bad.mp4" in data["errors"][0]["path"]
    assert "Probe failed" in data["errors"][0]["error"]


@pytest.mark.api
def test_scan_returns_summary(client: TestClient, tmp_path: Path) -> None:
    """Scan returns complete summary response."""
    (tmp_path / "video.mp4").touch()

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        return_value=mock_metadata,
    ):
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path)},
        )

    assert response.status_code == 200
    data = response.json()
    # Verify all fields are present
    assert "scanned" in data
    assert "new" in data
    assert "updated" in data
    assert "skipped" in data
    assert "errors" in data


# --- Delete endpoint tests ---


@pytest.mark.api
async def test_delete_video(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Delete removes video from database."""
    video = make_test_video()
    await video_repository.add(video)

    response = client.delete(f"/api/v1/videos/{video.id}")
    assert response.status_code == 204

    assert await video_repository.get(video.id) is None


@pytest.mark.api
def test_delete_video_not_found(client: TestClient) -> None:
    """Delete returns 404 for unknown ID."""
    response = client.delete("/api/v1/videos/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"
    assert "nonexistent" in data["detail"]["message"]


@pytest.mark.api
async def test_delete_video_with_file_deletion(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
    tmp_path: Path,
) -> None:
    """Delete with delete_file=true removes file from disk."""
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()
    assert video_file.exists()

    video = make_test_video(path=str(video_file.absolute()), filename="test_video.mp4")
    await video_repository.add(video)

    response = client.delete(f"/api/v1/videos/{video.id}?delete_file=true")
    assert response.status_code == 204

    assert await video_repository.get(video.id) is None
    assert not video_file.exists()


@pytest.mark.api
async def test_delete_video_without_file_deletion(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
    tmp_path: Path,
) -> None:
    """Delete without delete_file leaves file on disk."""
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()

    video = make_test_video(path=str(video_file.absolute()), filename="test_video.mp4")
    await video_repository.add(video)

    response = client.delete(f"/api/v1/videos/{video.id}")
    assert response.status_code == 204

    assert await video_repository.get(video.id) is None
    assert video_file.exists()


@pytest.mark.api
async def test_delete_video_file_already_missing(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Delete with delete_file=true succeeds even if file is already gone."""
    video = make_test_video(path="/nonexistent/video.mp4")
    await video_repository.add(video)

    response = client.delete(f"/api/v1/videos/{video.id}?delete_file=true")
    assert response.status_code == 204

    assert await video_repository.get(video.id) is None
