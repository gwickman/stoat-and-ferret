"""Smoke tests for Phase 4 preview, proxy, cache, thumbnail, and waveform endpoints.

Validates that all Phase 4 endpoints are reachable and return expected
response structures through the full HTTP stack with real Rust core.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings

from .conftest import create_adjacent_clips_timeline, scan_videos_and_wait


@pytest.fixture()
async def background_safe_client(tmp_path: Path) -> httpx.AsyncClient:
    """Async client with raise_app_exceptions=False for background-task endpoints.

    Endpoints that queue work via FastAPI BackgroundTasks (thumbnail strip,
    waveform) run their background tasks inline in ASGI transport. If the
    background task fails (e.g. FFmpeg error), the exception propagates even
    though the 202 response was already sent. This fixture suppresses those
    post-response exceptions so the smoke test can verify the HTTP contract.

    Args:
        tmp_path: Pytest-provided temporary directory unique to this test.

    Yields:
        An httpx.AsyncClient that won't raise on background task failures.
    """
    db_path = tmp_path / "smoke_test.db"

    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")

    get_settings.cache_clear()

    app = create_app()

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
        ) as client,
    ):
        yield client

    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db

    if orig_thumb is None:
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
    else:
        os.environ["STOAT_THUMBNAIL_DIR"] = orig_thumb

    get_settings.cache_clear()


async def test_preview_start_returns_202(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /api/v1/projects/{project_id}/preview/start returns 202 with session_id."""
    timeline_data = await create_adjacent_clips_timeline(smoke_client, videos_dir)
    project_id = timeline_data["project_id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/preview/start",
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "session_id" in body
    assert isinstance(body["session_id"], str)
    assert len(body["session_id"]) > 0


async def test_proxy_generate_returns_202(
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


async def test_cache_status_returns_200(
    smoke_client: httpx.AsyncClient,
) -> None:
    """GET /api/v1/preview/cache returns 200 with usage metrics."""
    resp = await smoke_client.get("/api/v1/preview/cache")
    assert resp.status_code == 200
    body = resp.json()
    assert "active_sessions" in body
    assert "used_bytes" in body
    assert "max_bytes" in body
    assert "usage_percent" in body
    assert isinstance(body["used_bytes"], int)
    assert isinstance(body["max_bytes"], int)
    assert isinstance(body["usage_percent"], float)


async def test_thumbnail_strip_generate_returns_202(
    background_safe_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /api/v1/videos/{video_id}/thumbnails/strip returns 202 with strip_id."""
    await scan_videos_and_wait(background_safe_client, videos_dir)

    resp = await background_safe_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await background_safe_client.post(
        f"/api/v1/videos/{video_id}/thumbnails/strip",
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "strip_id" in body
    assert body["status"] == "pending"
    assert isinstance(body["strip_id"], str)
    assert len(body["strip_id"]) > 0


async def test_waveform_generate_returns_202(
    background_safe_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /api/v1/videos/{video_id}/waveform returns 202 with waveform_id."""
    await scan_videos_and_wait(background_safe_client, videos_dir)

    resp = await background_safe_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await background_safe_client.post(
        f"/api/v1/videos/{video_id}/waveform",
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "waveform_id" in body
    assert body["status"] == "pending"
    assert isinstance(body["waveform_id"], str)
    assert len(body["waveform_id"]) > 0
