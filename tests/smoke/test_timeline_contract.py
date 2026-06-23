# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for timeline PUT empty-array (clearing) behavior.

Verifies that PUT /api/v1/projects/{id}/timeline with body [] deletes all
existing tracks and returns HTTP 200, as documented in operator-guide.md
"Clearing the Timeline" section (BL-387 option b: doc-only, behavior preserved).
"""

from __future__ import annotations

import httpx
import pytest


async def _create_project(client: httpx.AsyncClient, name: str = "timeline-contract-test") -> str:
    """Create a project and return its ID."""
    resp = await client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _put_tracks(
    client: httpx.AsyncClient,
    project_id: str,
    tracks: list[dict],
) -> dict:
    """PUT timeline tracks and return the response body."""
    resp = await client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=tracks,
    )
    assert resp.status_code == 200
    return resp.json()


async def test_empty_put_returns_200(smoke_client: httpx.AsyncClient) -> None:
    """PUT with empty array returns HTTP 200."""
    project_id = await _create_project(smoke_client)
    resp = await smoke_client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[],
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}; body={resp.json()}"


async def test_empty_put_deletes_all_tracks(smoke_client: httpx.AsyncClient) -> None:
    """PUT with empty array removes all previously-created tracks."""
    project_id = await _create_project(smoke_client)

    # Create two tracks
    timeline = await _put_tracks(
        smoke_client,
        project_id,
        [
            {"track_type": "video", "label": "V1"},
            {"track_type": "audio", "label": "A1"},
        ],
    )
    assert len(timeline["tracks"]) == 2

    # Clear all tracks
    resp = await smoke_client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tracks"] == [], f"Expected zero tracks after empty-PUT, got {len(body['tracks'])}"


async def test_empty_put_timeline_duration_zero(smoke_client: httpx.AsyncClient) -> None:
    """Timeline duration is 0.0 after clearing all tracks."""
    project_id = await _create_project(smoke_client)

    await _put_tracks(
        smoke_client,
        project_id,
        [{"track_type": "video", "label": "V1"}],
    )

    resp = await smoke_client.put(
        f"/api/v1/projects/{project_id}/timeline",
        json=[],
    )
    assert resp.status_code == 200
    assert resp.json()["duration"] == pytest.approx(0.0)


async def test_nonempty_put_creates_tracks(smoke_client: httpx.AsyncClient) -> None:
    """Normal PUT with tracks creates them correctly (regression guard)."""
    project_id = await _create_project(smoke_client)

    timeline = await _put_tracks(
        smoke_client,
        project_id,
        [
            {"track_type": "video", "label": "Main Video"},
            {"track_type": "audio", "label": "Main Audio"},
        ],
    )
    assert len(timeline["tracks"]) == 2
    labels = {t["label"] for t in timeline["tracks"]}
    assert labels == {"Main Video", "Main Audio"}
