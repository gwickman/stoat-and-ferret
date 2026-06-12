"""Smoke tests for generator clip API (BL-441).

Verifies that generator clips can be created via the clips endpoint without
requiring FFmpeg. Covers AC-4 of v079 feature 012-smoke-test-updates.
"""

from __future__ import annotations

import httpx


async def test_generator_clip_created_via_api(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/projects/{id}/clips with clip_type='generator' returns 201."""
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Generator Clip Smoke"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": {
                "type": "aevalsrc",
                "expr": "sin(2*PI*440*t)",
                "duration": 5.0,
            },
            "in_point": 0,
            "out_point": 240,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["clip_type"] == "generator", (
        f"Expected clip_type='generator', got {data['clip_type']!r}"
    )
    assert data["source_video_id"] is None, "Generator clip should have null source_video_id"
    assert data["generator_params"] is not None
    assert data["generator_params"]["type"] == "aevalsrc"


async def test_generator_clip_persists_in_list(smoke_client: httpx.AsyncClient) -> None:
    """Created generator clip appears in GET /api/v1/projects/{id}/clips."""
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Generator Clip Persist Smoke"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    create_resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "generator_params": {"type": "tone", "frequency": 440.0, "duration": 10.0},
            "in_point": 0,
            "out_point": 480,
            "timeline_position": 0,
        },
    )
    assert create_resp.status_code == 201
    clip_id = create_resp.json()["id"]

    list_resp = await smoke_client.get(f"/api/v1/projects/{project_id}/clips")
    assert list_resp.status_code == 200
    clips = list_resp.json()["clips"]
    assert any(c["id"] == clip_id for c in clips), "Created generator clip not found in list"


async def test_generator_clip_rejects_with_source_video_id(smoke_client: httpx.AsyncClient) -> None:
    """Generator clip with source_video_id set returns 422."""
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Generator Clip Validation Smoke"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    resp = await smoke_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "clip_type": "generator",
            "source_video_id": "00000000-0000-0000-0000-000000000001",
            "generator_params": {"type": "aevalsrc", "expr": "0", "duration": 1.0},
        },
    )
    assert resp.status_code == 422, (
        f"Expected 422 for generator+source_video_id, got {resp.status_code}"
    )
