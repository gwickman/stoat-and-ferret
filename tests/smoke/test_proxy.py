"""Smoke tests for proxy management API endpoints.

Validates proxy generation (POST), status retrieval (GET), deletion (DELETE),
and batch generation through the full HTTP stack with real app boot.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx

from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus
from stoat_ferret.db.proxy_repository import SQLiteProxyRepository

from .conftest import scan_videos_and_wait


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
