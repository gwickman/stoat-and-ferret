"""Smoke tests for video library search, detail, thumbnail, and delete (UC-02).

Validates pagination with limit/offset, FTS5 full-text search, single video
retrieval, thumbnail generation, and video deletion.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import scan_videos_and_wait


@pytest.mark.usefixtures("videos_dir")
async def test_uc02_library_search(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Search and paginate the video library after scanning."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Pagination: first page of 2
    resp = await smoke_client.get("/api/v1/videos?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6
    assert len(body["videos"]) == 2

    # Pagination: offset past end returns empty
    resp = await smoke_client.get("/api/v1/videos?limit=2&offset=6")
    assert resp.status_code == 200
    assert len(resp.json()["videos"]) == 0

    # FTS5 search: "running" matches running1.mp4 and running2.mp4
    resp = await smoke_client.get("/api/v1/videos/search?q=running")
    assert resp.status_code == 200
    search_body = resp.json()
    assert search_body["total"] == 2
    filenames = {v["filename"] for v in search_body["videos"]}
    assert filenames == {"running1.mp4", "running2.mp4"}

    # FTS5 search: nonexistent query returns 0 results
    resp = await smoke_client.get("/api/v1/videos/search?q=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["videos"] == []


@pytest.mark.usefixtures("videos_dir")
async def test_video_detail(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """GET /videos/{video_id} returns 200 with full metadata (BL-121 FR-001)."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Get a video ID from the list
    resp = await smoke_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    # GET detail
    resp = await smoke_client.get(f"/api/v1/videos/{video_id}")
    assert resp.status_code == 200
    body = resp.json()

    # Verify all required metadata fields are present
    required_fields = {
        "id",
        "path",
        "filename",
        "duration_frames",
        "frame_rate_numerator",
        "frame_rate_denominator",
        "width",
        "height",
        "video_codec",
        "file_size",
    }
    assert required_fields.issubset(body.keys()), f"Missing fields: {required_fields - body.keys()}"
    assert body["id"] == video_id
    assert body["duration_frames"] > 0
    assert body["width"] > 0
    assert body["height"] > 0
    assert body["file_size"] > 0


@pytest.mark.usefixtures("videos_dir")
async def test_video_detail_not_found(
    smoke_client: httpx.AsyncClient,
) -> None:
    """GET /videos/{fake_id} returns 404 (BL-121 FR-002)."""
    fake_id = str(uuid.uuid4())
    resp = await smoke_client.get(f"/api/v1/videos/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.usefixtures("videos_dir")
async def test_video_thumbnail(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """GET /videos/{video_id}/thumbnail returns JPEG image (BL-121 FR-003)."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Get a video ID
    resp = await smoke_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    # GET thumbnail
    resp = await smoke_client.get(f"/api/v1/videos/{video_id}/thumbnail")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert len(resp.content) > 0


@pytest.mark.usefixtures("videos_dir")
async def test_video_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """DELETE /videos/{video_id} returns 204, subsequent GET 404 (BL-121 FR-004/005)."""
    await scan_videos_and_wait(smoke_client, videos_dir)

    # Get list total before delete
    resp = await smoke_client.get("/api/v1/videos?limit=1&offset=0")
    assert resp.status_code == 200
    total_before = resp.json()["total"]
    assert total_before > 0

    # Pick a video to delete
    video_id = resp.json()["videos"][0]["id"]

    # DELETE (no delete_file — keep source on disk)
    resp = await smoke_client.delete(f"/api/v1/videos/{video_id}")
    assert resp.status_code == 204

    # Subsequent GET returns 404
    resp = await smoke_client.get(f"/api/v1/videos/{video_id}")
    assert resp.status_code == 404

    # List total decremented by 1
    resp = await smoke_client.get("/api/v1/videos?limit=1&offset=0")
    assert resp.status_code == 200
    assert resp.json()["total"] == total_before - 1
