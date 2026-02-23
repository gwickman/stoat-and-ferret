"""Tests for job status endpoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

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
        new_callable=AsyncMock,
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


@pytest.mark.api
def test_job_status_response_includes_progress_field(client: TestClient, tmp_path: Path) -> None:
    """GET /jobs/{id} response includes progress field."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert "progress" in data


@pytest.mark.api
def test_job_status_progress_none_for_completed_empty_scan(
    client: TestClient, tmp_path: Path
) -> None:
    """Progress is None for a completed job that scanned no files (no callback invoked)."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    data = response.json()
    assert data["status"] == "complete"
    # InMemoryJobQueue is a no-op for set_progress, so progress stays None
    assert data["progress"] is None


# --- Cancel endpoint tests ---


@pytest.mark.api
def test_cancel_job_not_found(client: TestClient) -> None:
    """POST /jobs/{id}/cancel returns 404 for unknown job."""
    response = client.post("/api/v1/jobs/nonexistent-id/cancel")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
def test_cancel_completed_job_returns_409(client: TestClient, tmp_path: Path) -> None:
    """POST /jobs/{id}/cancel returns 409 for already-completed job."""
    # Submit a scan that completes immediately (InMemoryJobQueue)
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Verify it's complete
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.json()["status"] == "complete"

    # Try to cancel
    cancel_resp = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_resp.status_code == 409
    data = cancel_resp.json()
    assert data["detail"]["code"] == "ALREADY_TERMINAL"


@pytest.mark.api
def test_cancel_pending_job_returns_200(
    client: TestClient,
    job_queue: InMemoryJobQueue,
    tmp_path: Path,
) -> None:
    """POST /jobs/{id}/cancel returns 200 for pending job.

    InMemoryJobQueue.cancel() is a no-op, but the endpoint should still succeed
    for non-terminal jobs. We test with a PENDING outcome by removing the handler
    and not configuring any outcome for the "pending-type".
    """
    # Manually add a pending job to the InMemoryJobQueue
    from stoat_ferret.jobs.queue import JobResult, JobStatus, _JobEntry

    job_id = "test-cancel-pending"
    entry = _JobEntry(job_id=job_id, job_type="scan", payload={})
    entry.result = JobResult(job_id=job_id, status=JobStatus.PENDING)
    job_queue._jobs[job_id] = entry

    cancel_resp = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_resp.status_code == 200
    data = cancel_resp.json()
    assert data["job_id"] == job_id
