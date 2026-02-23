"""Integration test: event loop stays responsive during directory scan.

Verifies that the event loop is NOT blocked during a scan by concurrently
polling the jobs endpoint while a scan with simulated-slow async ffprobe
runs.  This guards against regressions where blocking calls (e.g.
``time.sleep`` or synchronous subprocess) starve the event loop.

Threshold rationale
-------------------
The 2-second timeout is intentionally generous for in-process ASGI transport,
where typical responses arrive in <10 ms.  If this test becomes flaky on CI,
increase to 5 seconds before investigating further.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.ffmpeg.probe import VideoMetadata
from stoat_ferret.jobs.queue import AsyncioJobQueue

POLL_TIMEOUT_SECONDS = 2.0


def _make_slow_ffprobe(delay: float = 0.5) -> Any:
    """Return an async ffprobe substitute that sleeps before returning metadata.

    Args:
        delay: Seconds to sleep per call, simulating slow I/O.

    Returns:
        Async callable matching the ``ffprobe_video`` signature.
    """

    async def _slow_ffprobe(path: str, ffprobe_path: str = "ffprobe") -> VideoMetadata:
        await asyncio.sleep(delay)
        return VideoMetadata(
            duration_seconds=10.0,
            width=1920,
            height=1080,
            frame_rate_numerator=24,
            frame_rate_denominator=1,
            video_codec="h264",
            audio_codec="aac",
            file_size=1024,
        )

    return _slow_ffprobe


@pytest.mark.slow
@pytest.mark.integration
async def test_event_loop_responsive_during_scan(tmp_path: Path) -> None:
    """Event loop responds to HTTP requests while a slow scan is running.

    Creates several dummy video files, starts a scan that processes them with
    a simulated-slow async ffprobe (asyncio.sleep per file), then concurrently
    polls GET /api/v1/jobs/{id}.  The poll must complete within 2 seconds,
    proving the event loop is not blocked.

    If someone regresses to a blocking call (e.g. time.sleep or synchronous
    subprocess), the event loop would be starved and the poll would time out,
    failing this test.
    """
    # -- Arrange: create dummy video files --
    num_files = 5
    for i in range(num_files):
        (tmp_path / f"video_{i}.mp4").touch()

    # -- Build app with real AsyncioJobQueue --
    video_repo = AsyncInMemoryVideoRepository()
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    job_queue = AsyncioJobQueue()
    job_queue.register_handler(
        SCAN_JOB_TYPE,
        make_scan_handler(video_repo),
    )

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        job_queue=job_queue,
    )

    # Start the background job worker
    worker_task = asyncio.create_task(job_queue.process_jobs())

    try:
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Patch ffprobe_video at the scan-service level with the slow stub
            with patch(
                "stoat_ferret.api.services.scan.ffprobe_video",
                new=_make_slow_ffprobe(delay=0.5),
            ):
                # -- Act: submit scan --
                submit_resp = await client.post(
                    "/api/v1/videos/scan",
                    json={"path": str(tmp_path)},
                )
                assert submit_resp.status_code == 202
                job_id = submit_resp.json()["job_id"]

                # -- Assert: poll job status while scan is running --
                # With 5 files * 0.5 s each the scan takes ~2.5 s total,
                # so the first poll should happen while the scan is still in
                # progress.
                poll_response = await asyncio.wait_for(
                    client.get(f"/api/v1/jobs/{job_id}"),
                    timeout=POLL_TIMEOUT_SECONDS,
                )
                assert poll_response.status_code == 200
                data = poll_response.json()
                assert data["job_id"] == job_id
                # Status may be pending, running, or already complete —
                # the important assertion is that we got a response at all
                # within the timeout.
                assert data["status"] in {"pending", "running", "complete"}
    finally:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
