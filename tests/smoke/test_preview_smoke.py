"""Smoke test for preview lifecycle end-to-end (BL-393-AC-5).

Exercises POST /preview/start → poll GET /api/v1/preview/{session_id}
until a terminal state is reached. Skips gracefully if FFmpeg is
unavailable (NFR-002). Uses 30s timeout (NFR-001).
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import httpx
import pytest

from .conftest import create_adjacent_clips_timeline


@pytest.mark.smoke
async def test_preview_lifecycle_smoke(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Preview lifecycle end-to-end smoke: start, poll, no server errors (BL-393-AC-5).

    Creates a project with real video clips, starts a preview session, and polls
    GET /api/v1/preview/{session_id} every 1s for up to 30s until a terminal
    state (ready, error, expired) is reached. Verifies the server does not
    return 4xx/5xx during the lifecycle. Skips if FFmpeg is unavailable.
    """
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg not available — preview lifecycle requires real FFmpeg")

    timeline_data = await create_adjacent_clips_timeline(smoke_client, videos_dir)
    project_id = timeline_data["project_id"]

    start_resp = await smoke_client.post(f"/api/v1/projects/{project_id}/preview/start")
    if start_resp.status_code == 503:
        pytest.skip(f"Preview service unavailable: {start_resp.json()}")
    assert start_resp.status_code == 202, (
        f"Expected 202, got {start_resp.status_code}: {start_resp.text}"
    )
    session_id = start_resp.json()["session_id"]

    terminal_statuses = {"ready", "error", "expired"}
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 30.0
    final_status: str | None = None

    while loop.time() < deadline:
        status_resp = await smoke_client.get(f"/api/v1/preview/{session_id}")
        # Server must not return 4xx/5xx during the lifecycle
        assert status_resp.status_code == 200, (
            f"GET /preview/{session_id} returned {status_resp.status_code}: {status_resp.text}"
        )
        body = status_resp.json()
        final_status = body["status"]
        if final_status in terminal_statuses:
            break
        await asyncio.sleep(1.0)

    assert final_status is not None, "No status received from preview endpoint"
    # Accept any known status — the invariant is no server error (4xx/5xx) during polling
    assert final_status in terminal_statuses | {"initializing", "generating"}, (
        f"Unexpected final status: {final_status!r}"
    )


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requires ffmpeg on PATH")
async def test_preview_no_deadlock(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Preview session reaches terminal status without asyncio deadlock (BL-393-AC-1/2).

    Creates a project with real video clips, starts a preview session, and polls
    GET /api/v1/preview/{session_id} every 1s for up to 30s until a terminal
    state (ready, error, expired) is reached. Failure to reach terminal status
    within the window is treated as evidence of an asyncio deadlock.
    """
    timeline_data = await create_adjacent_clips_timeline(smoke_client, videos_dir)
    project_id = timeline_data["project_id"]

    start_resp = await smoke_client.post(f"/api/v1/projects/{project_id}/preview/start")
    if start_resp.status_code == 503:
        pytest.skip(f"Preview service unavailable: {start_resp.json()}")
    assert start_resp.status_code == 202, (
        f"Expected 202, got {start_resp.status_code}: {start_resp.text}"
    )
    session_id = start_resp.json()["session_id"]

    terminal_statuses = {"ready", "error", "expired"}
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 30.0
    final_status: str | None = None

    while loop.time() < deadline:
        status_resp = await smoke_client.get(f"/api/v1/preview/{session_id}")
        assert status_resp.status_code == 200, (
            f"GET /preview/{session_id} returned {status_resp.status_code}: {status_resp.text}"
        )
        final_status = status_resp.json()["status"]
        if final_status in terminal_statuses:
            break
        await asyncio.sleep(1.0)

    if final_status not in terminal_statuses:
        pytest.fail(
            f"Preview did not reach terminal status within 30s — possible asyncio deadlock "
            f"(last status: {final_status!r})"
        )
