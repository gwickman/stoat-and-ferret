"""Smoke tests for video library search and pagination (UC-02).

Validates pagination with limit/offset and FTS5 full-text search.
"""

from __future__ import annotations

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
