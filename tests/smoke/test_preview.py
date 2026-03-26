"""Smoke tests for preview session creation endpoint.

Validates that the preview start endpoint is reachable and returns expected
response structure when given a project with a populated timeline.
"""

from __future__ import annotations

from pathlib import Path

import httpx

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
