# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""FFmpeg-gated smoke tests for auxiliary stream counts (BL-408, AC-1 and AC-2).

These tests require real FFmpeg and the test corpus video files.
Run with: STOAT_TEST_FFMPEG=1 pytest tests/smoke/test_video_auxiliary_streams.py
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import scan_videos_and_wait

TEST_CORPUS = Path(__file__).parent.parent.parent / "videos" / "test-corpus"

SINTEL_MKV = TEST_CORPUS / "Sintel.2010.720p.mkv"
BBB_MOV = TEST_CORPUS / "big_buck_bunny_480p_h264.mov"


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
async def test_sintel_subtitle_count(smoke_client: httpx.AsyncClient) -> None:
    """Sintel MKV reports subtitle_count == 10 in VideoResponse (BL-408-AC-1)."""
    assert SINTEL_MKV.exists(), f"Sintel test fixture not found: {SINTEL_MKV}"

    sintel_dir = SINTEL_MKV.parent
    job = await scan_videos_and_wait(smoke_client, sintel_dir)
    assert job["status"].lower() == "completed"

    resp = await smoke_client.get("/api/v1/videos?limit=100")
    assert resp.status_code == 200
    videos = resp.json()["videos"]

    sintel = next((v for v in videos if v["filename"] == SINTEL_MKV.name), None)
    found = [v["filename"] for v in videos]
    assert sintel is not None, f"Sintel video not found in scanned results: {found}"

    detail = await smoke_client.get(f"/api/v1/videos/{sintel['id']}")
    assert detail.status_code == 200
    data = detail.json()

    assert data["subtitle_count"] == 10, (
        f"Expected 10 subtitle streams for Sintel, got {data['subtitle_count']}"
    )
    assert len(data["subtitle_streams"]) == 10


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
async def test_bbb_data_stream_count(smoke_client: httpx.AsyncClient) -> None:
    """BBB MOV reports data_count >= 1 in VideoResponse (BL-408-AC-2)."""
    assert BBB_MOV.exists(), f"BBB test fixture not found: {BBB_MOV}"

    bbb_dir = BBB_MOV.parent
    job = await scan_videos_and_wait(smoke_client, bbb_dir)
    assert job["status"].lower() == "completed"

    resp = await smoke_client.get("/api/v1/videos?limit=100")
    assert resp.status_code == 200
    videos = resp.json()["videos"]

    bbb = next((v for v in videos if v["filename"] == BBB_MOV.name), None)
    found = [v["filename"] for v in videos]
    assert bbb is not None, f"BBB MOV not found in scanned results: {found}"

    detail = await smoke_client.get(f"/api/v1/videos/{bbb['id']}")
    assert detail.status_code == 200
    data = detail.json()

    assert data["data_count"] >= 1, (
        f"Expected at least 1 data stream for BBB MOV, got {data['data_count']}"
    )
