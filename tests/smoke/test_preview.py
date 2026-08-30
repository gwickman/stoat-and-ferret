# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for preview session creation endpoint.

Validates that the preview start endpoint is reachable and returns expected
response structure when given a project with a populated timeline.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from .conftest import create_adjacent_clips_timeline


async def test_preview_session_creation(
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


async def test_multi_clip_preview_start(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Verify preview/start returns 202 with session_id for a 2-clip project (BL-797)."""
    timeline_data = await create_adjacent_clips_timeline(smoke_client, videos_dir)
    project_id = timeline_data["project_id"]
    assert timeline_data["clip_a_id"] != timeline_data["clip_b_id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/preview/start",
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "session_id" in body
    assert isinstance(body["session_id"], str)
    assert len(body["session_id"]) > 0


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires FFmpeg")
async def test_smoke_preview_with_effects_transition(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Preview with effects-shaped transition entry returns 202 (BL-853 FR-004, F002 fix)."""
    timeline_data = await create_adjacent_clips_timeline(smoke_client, videos_dir)
    project_id = timeline_data["project_id"]
    clip_a_id = timeline_data["clip_a_id"]
    clip_b_id = timeline_data["clip_b_id"]

    # Create an effects-shaped transition entry (nested parameters dict)
    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_a_id,
            "target_clip_id": clip_b_id,
            "transition_type": "fade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert resp.status_code == 201

    # Preview should return 202 (F002 fix: no KeyError on effects-shaped entries)
    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/preview/start",
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "session_id" in body
