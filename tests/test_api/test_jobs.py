"""Tests for job status endpoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.ffmpeg.probe import VideoMetadata
from stoat_ferret.jobs.queue import InMemoryJobQueue, JobOutcome


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
def test_get_job_not_found(client: TestClient) -> None:
    """GET /jobs/{id} returns 404 for unknown job ID."""
    response = client.get("/api/v1/jobs/nonexistent-job-id")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"
    assert "nonexistent-job-id" in data["detail"]["message"]


@pytest.mark.api
def test_get_job_status_complete(client: TestClient, tmp_path: Path) -> None:
    """GET /jobs/{id} returns complete status with result."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "complete"
    assert data["result"] is not None
    assert data["error"] is None


@pytest.mark.api
def test_get_job_status_failed(
    client: TestClient,
    job_queue: InMemoryJobQueue,
    tmp_path: Path,
) -> None:
    """GET /jobs/{id} returns failed status with error message."""
    job_queue.configure_outcome(
        "scan",
        JobOutcome.FAILURE,
        error="Scan handler failed",
    )
    # Remove the registered handler so the configured outcome is used
    job_queue._handlers.pop("scan", None)

    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "failed"
    assert data["error"] == "Scan handler failed"
    assert data["result"] is None


@pytest.mark.api
def test_job_id_is_uuid(client: TestClient, tmp_path: Path) -> None:
    """Job ID returned by scan is a valid UUID string."""
    import uuid

    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Should not raise ValueError
    parsed = uuid.UUID(job_id)
    assert str(parsed) == job_id


@pytest.mark.api
def test_full_async_scan_workflow(client: TestClient, tmp_path: Path) -> None:
    """Full async workflow: submit scan, poll status, verify result."""
    (tmp_path / "video.mp4").touch()

    mock_metadata = _make_mock_metadata()

    with patch(
        "stoat_ferret.api.services.scan.ffprobe_video",
        return_value=mock_metadata,
    ):
        # Step 1: Submit scan
        submit_resp = client.post(
            "/api/v1/videos/scan",
            json={"path": str(tmp_path)},
        )
        assert submit_resp.status_code == 202
        job_id = submit_resp.json()["job_id"]

    # Step 2: Poll for status
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    job = status_resp.json()

    # Step 3: Verify result
    assert job["status"] == "complete"
    assert job["result"]["scanned"] == 1
    assert job["result"]["new"] == 1
    assert job["error"] is None
