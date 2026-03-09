"""Smoke tests for video scan workflow (UC-01) and job cancellation (UC-12).

Validates the scan pipeline: POST scan -> poll job -> verify video metadata,
and the cancel pipeline: POST cancel -> verify status codes for race/terminal/invalid.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import (
    EXPECTED_VIDEOS,
    poll_job_until_terminal,
    scan_videos_and_wait,
)


@pytest.mark.usefixtures("videos_dir")
async def test_uc01_scan_videos(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Scan videos directory and verify all 6 videos with correct metadata."""
    job_status = await scan_videos_and_wait(smoke_client, videos_dir)
    assert job_status["status"].lower() == "complete"

    resp = await smoke_client.get("/api/v1/videos?limit=100")
    assert resp.status_code == 200
    body = resp.json()
    videos = body["videos"]
    assert body["total"] == 6

    by_name = {v["filename"]: v for v in videos}
    assert set(by_name.keys()) == set(EXPECTED_VIDEOS.keys())

    for filename, expected in EXPECTED_VIDEOS.items():
        video = by_name[filename]
        assert video["width"] == expected["width"], f"{filename} width"
        assert video["height"] == expected["height"], f"{filename} height"
        assert video["frame_rate_numerator"] == expected["fps_num"], f"{filename} fps_num"
        assert video["frame_rate_denominator"] == expected["fps_den"], f"{filename} fps_den"
        assert video["duration_frames"] == expected["frames"], f"{filename} frames"
        assert video["video_codec"] == expected["video_codec"], f"{filename} video_codec"
        assert video["audio_codec"] == expected["audio_codec"], f"{filename} audio_codec"


@pytest.mark.usefixtures("videos_dir")
async def test_uc12_cancel_scan(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Cancel a scan job and verify status codes for race, terminal, and invalid."""
    # Start a scan
    resp = await smoke_client.post(
        "/api/v1/videos/scan",
        json={"path": str(videos_dir), "recursive": True},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Immediately try to cancel — accept 200 (cancelled) or 409 (already finished)
    resp = await smoke_client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code in {200, 409}

    # Wait for job to reach terminal state before re-cancelling.
    # The cancel flag is set but the job may still be processing.
    await poll_job_until_terminal(smoke_client, job_id)

    # Now the job is terminal — cancelling again should return 409
    resp = await smoke_client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 409

    # Cancel on nonexistent job ID returns 404
    fake_id = str(uuid.uuid4())
    resp = await smoke_client.post(f"/api/v1/jobs/{fake_id}/cancel")
    assert resp.status_code == 404
