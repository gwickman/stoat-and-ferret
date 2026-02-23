"""Tests for video endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.services.scan import make_scan_handler, scan_directory
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
    """List respects limit parameter and total reflects full dataset."""
    for _ in range(5):
        await video_repository.add(make_test_video())

    response = client.get("/api/v1/videos?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 3
    assert data["limit"] == 3
    assert data["total"] == 5


@pytest.mark.api
async def test_list_videos_respects_offset(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """List respects offset parameter and total reflects full dataset."""
    for _ in range(5):
        await video_repository.add(make_test_video())

    response = client.get("/api/v1/videos?offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 3
    assert data["offset"] == 2
    assert data["total"] == 5


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

    response = client.get("/api/v1/videos/search?q=test&limit=3")
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


def _submit_scan(client: TestClient, path: str, **kwargs: object) -> str:
    """Submit a scan job and return the job ID.

    Args:
        client: Test client.
        path: Directory to scan.
        **kwargs: Additional scan request fields.

    Returns:
        The job ID string.
    """
    payload: dict[str, object] = {"path": path, **kwargs}
    response = client.post("/api/v1/videos/scan", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    return data["job_id"]


def _get_job_result(client: TestClient, job_id: str) -> dict[str, object]:
    """Poll job status and return the response.

    Args:
        client: Test client.
        job_id: Job ID to poll.

    Returns:
        The job status response dict.
    """
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    return response.json()


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
def test_scan_returns_job_id(client: TestClient, tmp_path: Path) -> None:
    """Scan returns 202 with a job ID."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)
    assert len(data["job_id"]) > 0


@pytest.mark.api
def test_scan_empty_directory(client: TestClient, tmp_path: Path) -> None:
    """Scan of empty directory returns zeros via job result."""
    job_id = _submit_scan(client, str(tmp_path))
    job = _get_job_result(client, job_id)

    assert job["status"] == "complete"
    result = job["result"]
    assert result["scanned"] == 0
    assert result["new"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 0
    assert result["errors"] == []


@pytest.mark.api
def test_scan_finds_video_files(client: TestClient, tmp_path: Path) -> None:
    """Scan finds and adds video files."""
    (tmp_path / "video1.mp4").touch()
    (tmp_path / "video2.mkv").touch()
    (tmp_path / "not_video.txt").touch()

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        job_id = _submit_scan(client, str(tmp_path))

    job = _get_job_result(client, job_id)
    assert job["status"] == "complete"
    result = job["result"]
    assert result["scanned"] == 2
    assert result["new"] == 2
    assert result["updated"] == 0
    assert result["skipped"] == 0
    assert result["errors"] == []


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
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        job_id = _submit_scan(client, str(tmp_path), recursive=True)

    job = _get_job_result(client, job_id)
    assert job["status"] == "complete"
    result = job["result"]
    assert result["scanned"] == 2
    assert result["new"] == 2


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
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        job_id = _submit_scan(client, str(tmp_path), recursive=False)

    job = _get_job_result(client, job_id)
    assert job["status"] == "complete"
    result = job["result"]
    assert result["scanned"] == 1
    assert result["new"] == 1


@pytest.mark.api
async def test_scan_updates_existing_videos(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
    tmp_path: Path,
) -> None:
    """Scan updates existing videos in repository."""
    video_path = tmp_path / "existing.mp4"
    video_path.touch()

    existing_video = make_test_video(
        path=str(video_path.absolute()),
        filename="existing.mp4",
    )
    await video_repository.add(existing_video)

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        job_id = _submit_scan(client, str(tmp_path))

    job = _get_job_result(client, job_id)
    assert job["status"] == "complete"
    result = job["result"]
    assert result["scanned"] == 1
    assert result["new"] == 0
    assert result["updated"] == 1


@pytest.mark.api
def test_scan_handles_errors_gracefully(client: TestClient, tmp_path: Path) -> None:
    """Scan continues even if individual files fail."""
    (tmp_path / "good.mp4").touch()
    (tmp_path / "bad.mp4").touch()

    mock_metadata = _make_mock_metadata()

    async def mock_probe(path: str) -> VideoMetadata:
        if "bad" in path:
            raise ValueError("Probe failed")
        return mock_metadata

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        side_effect=mock_probe,
    ):
        job_id = _submit_scan(client, str(tmp_path))

    job = _get_job_result(client, job_id)
    assert job["status"] == "complete"
    result = job["result"]
    assert result["scanned"] == 2
    assert result["new"] == 1
    assert len(result["errors"]) == 1
    assert "bad.mp4" in result["errors"][0]["path"]
    assert "Probe failed" in result["errors"][0]["error"]


@pytest.mark.api
def test_scan_returns_summary(client: TestClient, tmp_path: Path) -> None:
    """Scan job result contains complete summary."""
    (tmp_path / "video.mp4").touch()

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        job_id = _submit_scan(client, str(tmp_path))

    job = _get_job_result(client, job_id)
    assert job["status"] == "complete"
    result = job["result"]
    assert "scanned" in result
    assert "new" in result
    assert "updated" in result
    assert "skipped" in result
    assert "errors" in result


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


# --- Progress callback tests ---


@pytest.mark.api
async def test_scan_directory_calls_progress_callback(tmp_path: Path) -> None:
    """scan_directory calls progress callback after each file."""
    (tmp_path / "a.mp4").touch()
    (tmp_path / "b.mp4").touch()
    (tmp_path / "c.mp4").touch()

    mock_metadata = _make_mock_metadata()
    repo = AsyncInMemoryVideoRepository()
    progress_values: list[float] = []

    def on_progress(value: float) -> None:
        progress_values.append(value)

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        result = await scan_directory(
            path=str(tmp_path),
            recursive=True,
            repository=repo,
            progress_callback=on_progress,
        )

    assert result.scanned == 3
    assert len(progress_values) == 3
    assert progress_values[-1] == pytest.approx(1.0)
    # Each value should be scanned/total
    for i, val in enumerate(progress_values, 1):
        assert val == pytest.approx(i / 3)


@pytest.mark.api
async def test_scan_directory_no_callback_no_error(tmp_path: Path) -> None:
    """scan_directory works fine without a progress callback."""
    (tmp_path / "video.mp4").touch()

    mock_metadata = _make_mock_metadata()
    repo = AsyncInMemoryVideoRepository()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        result = await scan_directory(
            path=str(tmp_path),
            recursive=True,
            repository=repo,
        )

    assert result.scanned == 1


@pytest.mark.api
async def test_make_scan_handler_wires_progress_to_queue(tmp_path: Path) -> None:
    """make_scan_handler creates progress callback that calls queue.set_progress."""
    (tmp_path / "video.mp4").touch()

    mock_metadata = _make_mock_metadata()
    repo = AsyncInMemoryVideoRepository()
    mock_queue = MagicMock()

    handler = make_scan_handler(repo, queue=mock_queue)

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        await handler("scan", {"path": str(tmp_path), "_job_id": "test-job-123"})

    mock_queue.set_progress.assert_called_with("test-job-123", 1.0)


# --- Scan cancellation tests ---


@pytest.mark.api
async def test_scan_directory_breaks_on_cancel_event(tmp_path: Path) -> None:
    """scan_directory breaks file loop when cancel_event is set."""
    import asyncio

    (tmp_path / "a.mp4").touch()
    (tmp_path / "b.mp4").touch()
    (tmp_path / "c.mp4").touch()

    mock_metadata = _make_mock_metadata()
    repo = AsyncInMemoryVideoRepository()

    cancel_event = asyncio.Event()
    cancel_event.set()  # Set before scan starts — should process 0 files

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        result = await scan_directory(
            path=str(tmp_path),
            recursive=True,
            repository=repo,
            cancel_event=cancel_event,
        )

    assert result.scanned == 0
    assert result.new == 0


@pytest.mark.api
async def test_scan_directory_returns_partial_results_on_cancel(tmp_path: Path) -> None:
    """Cancelled scan returns partial results (files scanned before cancellation)."""
    import asyncio

    (tmp_path / "a.mp4").touch()
    (tmp_path / "b.mp4").touch()
    (tmp_path / "c.mp4").touch()

    mock_metadata = _make_mock_metadata()
    repo = AsyncInMemoryVideoRepository()
    cancel_event = asyncio.Event()
    call_count = 0

    async def probe_then_cancel(path: str) -> VideoMetadata:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            cancel_event.set()
        return mock_metadata

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        side_effect=probe_then_cancel,
    ):
        result = await scan_directory(
            path=str(tmp_path),
            recursive=True,
            repository=repo,
            cancel_event=cancel_event,
        )

    # Should have processed some but not all files
    assert result.scanned < 3
    assert result.new > 0
