# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for timeline markers API (BL-419).

Covers CRUD lifecycle, overlap rejection (section type), start-time ordering,
and 404 on a non-existent project.
"""

from __future__ import annotations

import httpx


async def _create_project(client: httpx.AsyncClient, name: str = "Markers Test") -> str:
    """Create a project and return its ID."""
    resp = await client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_marker_crud_lifecycle(smoke_client: httpx.AsyncClient) -> None:
    """Full create/list/update/delete smoke path (FR-001-AC-1)."""
    pid = await _create_project(smoke_client)

    resp = await smoke_client.post(
        f"/api/v1/projects/{pid}/markers",
        json={"start_time": 10.0, "end_time": None, "name": "Intro", "region_type": "point"},
    )
    assert resp.status_code == 201
    marker = resp.json()
    mid = marker["id"]
    assert marker["start_time"] == 10.0
    assert marker["region_type"] == "point"
    assert marker["name"] == "Intro"

    resp = await smoke_client.get(f"/api/v1/projects/{pid}/markers")
    assert resp.status_code == 200
    assert any(m["id"] == mid for m in resp.json())

    resp = await smoke_client.patch(
        f"/api/v1/projects/{pid}/markers/{mid}",
        json={"name": "Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"

    resp = await smoke_client.delete(f"/api/v1/projects/{pid}/markers/{mid}")
    assert resp.status_code == 204


async def test_overlapping_section_rejected(smoke_client: httpx.AsyncClient) -> None:
    """Second overlapping section marker is rejected with 422 (FR-001-AC-2)."""
    pid = await _create_project(smoke_client, "Overlap Test")

    resp = await smoke_client.post(
        f"/api/v1/projects/{pid}/markers",
        json={"start_time": 0.0, "end_time": 10.0, "name": "First", "region_type": "section"},
    )
    assert resp.status_code == 201

    resp = await smoke_client.post(
        f"/api/v1/projects/{pid}/markers",
        json={"start_time": 5.0, "end_time": 15.0, "name": "Overlap", "region_type": "section"},
    )
    assert resp.status_code == 422


async def test_markers_ordered_by_start_time(smoke_client: httpx.AsyncClient) -> None:
    """Markers are returned in start_time ASC order regardless of creation order (FR-001-AC-3)."""
    pid = await _create_project(smoke_client, "Ordering Test")

    for start, name in [(30.0, "Third"), (10.0, "First"), (20.0, "Second")]:
        resp = await smoke_client.post(
            f"/api/v1/projects/{pid}/markers",
            json={"start_time": start, "end_time": None, "name": name, "region_type": "point"},
        )
        assert resp.status_code == 201

    resp = await smoke_client.get(f"/api/v1/projects/{pid}/markers")
    assert resp.status_code == 200
    markers = resp.json()
    assert len(markers) == 3
    start_times = [m["start_time"] for m in markers]
    assert start_times == sorted(start_times)


async def test_marker_on_nonexistent_project(smoke_client: httpx.AsyncClient) -> None:
    """Creating a marker on a non-existent project returns 404 (FR-001-AC-4)."""
    resp = await smoke_client.post(
        "/api/v1/projects/nonexistent-project-id/markers",
        json={"start_time": 0.0, "end_time": None, "name": "Ghost", "region_type": "point"},
    )
    assert resp.status_code == 404
