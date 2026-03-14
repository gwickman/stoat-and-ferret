"""Smoke test fixtures and async helpers.

Provides shared infrastructure for API-level smoke tests exercising the full
backend stack (HTTP -> FastAPI -> Services -> PyO3/Rust -> SQLite) with real
video files.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings

VIDEOS_DIR = Path(__file__).parent.parent.parent / "videos"

EXPECTED_VIDEOS: dict[str, dict[str, Any]] = {
    "120449-720880553_medium.mp4": {
        "duration_seconds": 35.84,
        "width": 1280,
        "height": 720,
        "fps_num": 30000,
        "fps_den": 1001,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 1074,
    },
    "15748-266043652_medium.mp4": {
        "duration_seconds": 28.93,
        "width": 1280,
        "height": 720,
        "fps_num": 25,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 723,
    },
    "78888-568004778_medium.mp4": {
        "duration_seconds": 29.73,
        "width": 1280,
        "height": 720,
        "fps_num": 60,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 1784,
    },
    "81872-577880797_medium.mp4": {
        "duration_seconds": 50.99,
        "width": 1280,
        "height": 720,
        "fps_num": 60,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 3059,
    },
    "running1.mp4": {
        "duration_seconds": 29.60,
        "width": 960,
        "height": 540,
        "fps_num": 30,
        "fps_den": 1,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 888,
    },
    "running2.mp4": {
        "duration_seconds": 22.32,
        "width": 960,
        "height": 540,
        "fps_num": 30000,
        "fps_den": 1001,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frames": 669,
    },
}


@pytest.fixture(scope="session")
def videos_dir() -> Path:
    """Path to the real videos/ directory in the repo root.

    Asserts the directory exists and contains at least 6 MP4 files.

    Returns:
        Path to the videos directory.

    Raises:
        AssertionError: If videos directory is missing or has too few files.
    """
    assert VIDEOS_DIR.exists(), f"Videos directory not found: {VIDEOS_DIR}"
    mp4_files = list(VIDEOS_DIR.glob("*.mp4"))
    assert len(mp4_files) >= 6, (
        f"Expected at least 6 MP4 files in {VIDEOS_DIR}, found {len(mp4_files)}"
    )
    return VIDEOS_DIR


@pytest.fixture()
async def smoke_client(tmp_path: Path) -> httpx.AsyncClient:
    """Async httpx client connected to a fresh FastAPI app with isolated database.

    Each test gets its own SQLite database in tmp_path, ensuring full isolation.
    The Rust core is real (not mocked). Environment variables are set to point
    the app's Settings at the temporary paths and cleaned up afterward.

    Args:
        tmp_path: Pytest-provided temporary directory unique to this test.

    Yields:
        An httpx.AsyncClient connected to the app via ASGITransport.
    """
    db_path = tmp_path / "smoke_test.db"

    # Save original env vars
    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")

    # Clear cached settings so the app picks up new env vars
    get_settings.cache_clear()

    app = create_app()

    # Manually invoke the lifespan to initialise app.state (db, job_queue, etc.).
    # httpx ASGITransport does not send ASGI lifespan events, so the app's
    # startup/shutdown hooks would never run otherwise.
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client

    # Restore original env vars
    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db

    if orig_thumb is None:
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
    else:
        os.environ["STOAT_THUMBNAIL_DIR"] = orig_thumb

    get_settings.cache_clear()


async def poll_job_until_terminal(
    client: httpx.AsyncClient,
    job_id: str,
    *,
    timeout: float = 30.0,
    interval: float = 0.5,
) -> dict[str, Any]:
    """Poll GET /api/v1/jobs/{job_id} until status is terminal.

    Args:
        client: The httpx async client to use.
        job_id: The job ID to poll.
        timeout: Maximum seconds to wait (default 30).
        interval: Seconds between polls (default 0.5).

    Returns:
        The final job status response body.

    Raises:
        asyncio.TimeoutError: If the job does not reach terminal status in time.
    """
    terminal_statuses = {"complete", "failed", "timeout", "cancelled"}
    deadline = asyncio.get_event_loop().time() + timeout
    body: dict[str, Any] = {}

    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        if body["status"].lower() in terminal_statuses:
            return body
        await asyncio.sleep(interval)

    raise asyncio.TimeoutError(
        f"Job {job_id} did not reach terminal status within {timeout}s. "
        f"Last status: {body.get('status', 'unknown')}"
    )


async def scan_videos_and_wait(
    client: httpx.AsyncClient,
    videos_path: str | Path,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Submit a scan request and poll until complete.

    Args:
        client: The httpx async client to use.
        videos_path: Path to the directory to scan.
        timeout: Maximum seconds to wait (default 30).

    Returns:
        The job status response body after reaching terminal state.
    """
    resp = await client.post(
        "/api/v1/videos/scan",
        json={"path": str(videos_path), "recursive": True},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    return await poll_job_until_terminal(client, job_id, timeout=timeout)


async def create_project_with_clips(
    client: httpx.AsyncClient,
    project_name: str,
    video_ids: list[str],
    clips: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Create a project and add clips to it.

    Each clip dict must contain: source_video_id, in_point, out_point,
    timeline_position (all frame-based integers).

    Args:
        client: The httpx async client to use.
        project_name: Name of the project to create.
        video_ids: List of video IDs (unused directly, but available for callers).
        clips: List of clip definition dicts.

    Returns:
        Tuple of (project_response, list_of_clip_responses).
    """
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": project_name},
    )
    assert proj_resp.status_code == 201
    project = proj_resp.json()
    project_id = project["id"]

    clip_responses = []
    for clip in clips:
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json=clip,
        )
        assert clip_resp.status_code == 201
        clip_responses.append(clip_resp.json())

    return project, clip_responses


async def create_adjacent_clips_timeline(
    client: httpx.AsyncClient,
    videos_dir: Path,
) -> dict[str, Any]:
    """Create a project with two adjacent clips on the same timeline track.

    Scans videos, creates a project, sets up a timeline with one video track,
    and adds two clips positioned so that clip_a.timeline_end == clip_b.timeline_start.

    Args:
        client: The httpx async client to use.
        videos_dir: Path to the videos directory.

    Returns:
        Dict with keys: project_id, track_id, clip_a_id, clip_b_id.
    """
    await scan_videos_and_wait(client, videos_dir)

    # Pick a video
    resp = await client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video = resp.json()["videos"][0]
    video_id = video["id"]

    # Create project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Adjacent Clips Transition Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Create two clips from the same video
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201
    clip_a_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 100,
        },
    )
    assert resp.status_code == 201
    clip_b_id = resp.json()["id"]

    # PUT timeline with a video track
    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[{"track_type": "video", "label": "V1"}],
    )
    assert resp.status_code == 200
    track_id = resp.json()["tracks"][0]["id"]

    # Add clip A: 0.0 - 5.0
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip_a_id,
            "track_id": track_id,
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert resp.status_code == 201

    # Add clip B: 5.0 - 10.0 (adjacent: clip_a.timeline_end == clip_b.timeline_start)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/timeline/clips",
        json={
            "clip_id": clip_b_id,
            "track_id": track_id,
            "timeline_start": 5.0,
            "timeline_end": 10.0,
        },
    )
    assert resp.status_code == 201

    # Verify adjacency via GET
    resp = await client.get(f"/api/v1/projects/{project_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    track = timeline["tracks"][0]
    clips_on_track = sorted(track["clips"], key=lambda c: c["timeline_start"])
    assert len(clips_on_track) == 2
    assert clips_on_track[0]["timeline_end"] == pytest.approx(
        clips_on_track[1]["timeline_start"]
    ), "Clips must be adjacent: clip_a.timeline_end == clip_b.timeline_start"

    return {
        "project_id": project_id,
        "track_id": track_id,
        "clip_a_id": clip_a_id,
        "clip_b_id": clip_b_id,
    }


@pytest.fixture()
async def sample_project(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> dict[str, Any]:
    """Create the 'Running Montage' sample project with clips.

    Scans videos, creates a project at 1280x720 @ 30fps, and adds 4 clips.
    Returns a dict with project, clip_ids, and video_ids for test scenarios.

    Args:
        smoke_client: The per-test async client fixture.
        videos_dir: Path to the videos directory.

    Returns:
        Dict with keys: project, project_id, video_ids, clip_ids.
    """
    client = smoke_client

    # Scan videos
    await scan_videos_and_wait(client, videos_dir)

    # Resolve video IDs
    resp = await client.get("/api/v1/videos?limit=100")
    videos = resp.json()["videos"]
    name_to_id = {v["filename"]: v["id"] for v in videos}

    sample_videos = [
        "78888-568004778_medium.mp4",
        "running1.mp4",
        "running2.mp4",
        "81872-577880797_medium.mp4",
    ]
    video_ids = [name_to_id[fn] for fn in sample_videos]

    # Create project at 1280x720 @ 30fps
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Running Montage",
            "output_width": 1280,
            "output_height": 720,
            "output_fps": 30,
        },
    )
    project = resp.json()
    project_id = project["id"]

    # Add 4 clips (in_point/out_point/timeline_position are integer frames)
    clip_defs = [
        (0, 60, 300, 0),  # Clip 1: establishing shot
        (1, 90, 540, 300),  # Clip 2: running 1
        (2, 30, 360, 750),  # Clip 3: running 2
        (3, 150, 450, 1080),  # Clip 4: outro
    ]
    clip_ids = []
    for vid_idx, in_pt, out_pt, tl_pos in clip_defs:
        resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video_ids[vid_idx],
                "in_point": in_pt,
                "out_point": out_pt,
                "timeline_position": tl_pos,
            },
        )
        clip_ids.append(resp.json()["id"])

    return {
        "project": project,
        "project_id": project_id,
        "video_ids": video_ids,
        "clip_ids": clip_ids,
    }
