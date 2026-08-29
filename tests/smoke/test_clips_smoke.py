# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for clip timeline field propagation (BL-831)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import scan_videos_and_wait


@pytest.mark.usefixtures("videos_dir")
async def test_smoke_clip_timeline_propagation(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Regression guard: POST /clips with clip_type=file, timeline_start/end propagates to response.

    Guards BL-831 fix (file and generator clip branches now pass timeline_start/timeline_end
    to the Clip constructor instead of silently dropping them).
    """
    await scan_videos_and_wait(smoke_client, videos_dir)

    resp = await smoke_client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video_id = resp.json()["videos"][0]["id"]

    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Timeline Propagation Smoke"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "file",
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
            "timeline_start": 0.0,
            "timeline_end": 5.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["timeline_start"] == 0.0, (
        f"timeline_start was silently dropped (got {data['timeline_start']!r})"
    )
    assert data["timeline_end"] == 5.0, (
        f"timeline_end was silently dropped (got {data['timeline_end']!r})"
    )
