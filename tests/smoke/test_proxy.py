"""Smoke tests for proxy management API endpoints.

Validates proxy generation (POST), status retrieval (GET), deletion (DELETE),
and batch generation through the full HTTP stack with real app boot.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository
from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus, Video
from stoat_ferret.db.proxy_repository import SQLiteProxyRepository

from .conftest import poll_job_until_terminal, scan_videos_and_wait


def _get_proxy_repo(client: httpx.AsyncClient) -> SQLiteProxyRepository:
    """Extract proxy repository from the ASGI transport's app state.

    Args:
        client: The httpx async client connected via ASGITransport.

    Returns:
        SQLiteProxyRepository backed by the live test database.
    """
    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    return SQLiteProxyRepository(db)


async def _seed_proxy(client: httpx.AsyncClient, video_id: str) -> ProxyFile:
    """Insert a ready proxy record directly into the database.

    Creates a proxy with status READY for the given video, bypassing
    the FFmpeg transcoding pipeline.

    Args:
        client: The httpx async client connected via ASGITransport.
        video_id: Source video ID for the proxy.

    Returns:
        The inserted ProxyFile record.
    """
    repo = _get_proxy_repo(client)
    now = datetime.now(timezone.utc)
    proxy = ProxyFile(
        id=ProxyFile.new_id(),
        source_video_id=video_id,
        quality=ProxyQuality.MEDIUM,
        file_path="/tmp/test_proxy.mp4",
        file_size_bytes=1024,
        status=ProxyStatus.PENDING,
        source_checksum="abc123",
        generated_at=None,
        last_accessed_at=now,
    )
    await repo.add(proxy)
    await repo.update_status(proxy.id, ProxyStatus.GENERATING)
    await repo.update_status(proxy.id, ProxyStatus.READY, file_size_bytes=1024)
    return proxy


async def test_proxy_generate(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /api/v1/videos/{video_id}/proxy returns 202 with job_id."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    resp = await smoke_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await smoke_client.post(f"/api/v1/videos/{video_id}/proxy")
    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert isinstance(body["job_id"], str)
    assert len(body["job_id"]) > 0


async def test_proxy_status(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """GET /api/v1/videos/{video_id}/proxy returns proxy with expected fields."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    resp = await smoke_client.get("/api/v1/videos?limit=1")
    video_id = resp.json()["videos"][0]["id"]

    # Seed a proxy record directly (bypasses FFmpeg)
    await _seed_proxy(smoke_client, video_id)

    resp = await smoke_client.get(f"/api/v1/videos/{video_id}/proxy")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "quality" in body
    assert "file_size_bytes" in body
    assert body["status"] == "ready"
    assert body["quality"] == "medium"
    assert body["file_size_bytes"] == 1024
    assert body["source_video_id"] == video_id


async def test_proxy_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """DELETE /api/v1/videos/{video_id}/proxy removes proxy and returns freed_bytes."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    resp = await smoke_client.get("/api/v1/videos?limit=1")
    video_id = resp.json()["videos"][0]["id"]

    await _seed_proxy(smoke_client, video_id)

    resp = await smoke_client.delete(f"/api/v1/videos/{video_id}/proxy")
    assert resp.status_code == 200
    body = resp.json()
    assert "freed_bytes" in body
    assert body["freed_bytes"] == 1024

    # Verify proxy is gone
    resp = await smoke_client.get(f"/api/v1/videos/{video_id}/proxy")
    assert resp.status_code == 404


async def test_proxy_batch(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /api/v1/proxy/batch returns queued and skipped lists."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    resp = await smoke_client.get("/api/v1/videos?limit=3")
    assert resp.status_code == 200
    videos = resp.json()["videos"]
    video_ids = [v["id"] for v in videos[:3]]

    # Seed a proxy for the first video so it gets skipped
    await _seed_proxy(smoke_client, video_ids[0])

    resp = await smoke_client.post(
        "/api/v1/proxy/batch",
        json={"video_ids": video_ids},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "queued" in body
    assert "skipped" in body
    assert isinstance(body["queued"], list)
    assert isinstance(body["skipped"], list)
    # First video should be skipped (already has proxy), others queued
    assert video_ids[0] in body["skipped"]
    assert len(body["queued"]) == len(video_ids) - 1


async def test_proxy_odd_dimension(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Proxy generation succeeds for a source with odd width (BL-406-AC-1).

    Inserts a video record with odd width (853) pointing to a real MP4, submits a
    proxy job, waits for completion, and asserts status='ready' with non-zero file size.
    Skips if FFmpeg is not installed.
    """
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg not available — odd-dimension proxy requires real FFmpeg")

    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    app = transport.app  # type: ignore[union-attr]
    db = app.state.db

    video_repo = AsyncSQLiteVideoRepository(db)
    now = datetime.now(timezone.utc)
    source_path = str(videos_dir / "running1.mp4")
    video = Video(
        id=Video.new_id(),
        path=source_path,
        filename="running1_odd_dim_test.mp4",
        duration_frames=888,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=853,
        height=480,
        video_codec="h264",
        audio_codec="aac",
        file_size=1024,
        created_at=now,
        updated_at=now,
    )
    await video_repo.add(video)

    resp = await smoke_client.post(f"/api/v1/videos/{video.id}/proxy")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    job_body = await poll_job_until_terminal(smoke_client, job_id, timeout=60.0)
    assert job_body["status"] == "completed", (
        f"Proxy job failed — odd-dim rounding may not be applied. "
        f"Job status: {job_body['status']!r}, error: {job_body.get('error')!r}"
    )

    proxy_resp = await smoke_client.get(f"/api/v1/videos/{video.id}/proxy")
    assert proxy_resp.status_code == 200
    proxy_body = proxy_resp.json()
    assert proxy_body["status"] == "ready"
    assert proxy_body["file_size_bytes"] > 0


async def test_proxy_failure_terminal_ws_event(
    smoke_client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    """A failed proxy job emits exactly one proxy.failed WS event (BL-406-AC-3).

    Creates a fake video record pointing to an invalid file, submits a proxy job,
    waits for the job to fail, then asserts exactly one proxy.failed event for the
    job_id appears in the WS replay buffer. Skips if FFmpeg is not installed.
    """
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg not available — proxy failure path requires real FFmpeg")

    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    app = transport.app  # type: ignore[union-attr]
    db = app.state.db
    ws_manager = app.state.ws_manager

    # Create a file that exists but is not a valid video; FFmpeg will return non-zero
    fake_video = tmp_path / "invalid_video.mp4"
    fake_video.write_bytes(b"not a real video file")

    video_repo = AsyncSQLiteVideoRepository(db)
    now = datetime.now(timezone.utc)
    video = Video(
        id=Video.new_id(),
        path=str(fake_video),
        filename="invalid_video_test.mp4",
        duration_frames=900,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=960,
        height=540,
        video_codec="h264",
        audio_codec="aac",
        file_size=21,
        created_at=now,
        updated_at=now,
    )
    await video_repo.add(video)

    resp = await smoke_client.post(f"/api/v1/videos/{video.id}/proxy")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    await poll_job_until_terminal(smoke_client, job_id, timeout=30.0)

    # After terminal state, proxy.failed must be in the WS replay buffer
    deadline = asyncio.get_event_loop().time() + 5.0
    proxy_failed_events: list[dict] = []
    while asyncio.get_event_loop().time() < deadline:
        proxy_failed_events = [
            e
            for e in ws_manager._replay_buffer
            if e.get("type") == "proxy.failed" and e.get("payload", {}).get("job_id") == job_id
        ]
        if proxy_failed_events:
            break
        await asyncio.sleep(0.1)

    assert len(proxy_failed_events) == 1, (
        f"Expected exactly 1 proxy.failed event for job {job_id}, "
        f"found {len(proxy_failed_events)}. "
        f"Buffer types: {[e.get('type') for e in ws_manager._replay_buffer]}"
    )
