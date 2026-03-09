"""Smoke tests for effects lifecycle (UC-05, UC-06, UC-11).

Validates the deepest stack path: API -> EffectRegistry -> Rust PyO3
filter builders -> filter string generation. Covers effects catalog,
apply/update/delete, and speed control with effect stacking.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.smoke.conftest import scan_videos_and_wait


@pytest.mark.usefixtures("videos_dir")
async def test_uc05_effects_catalog_and_apply(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """List effect catalog, preview drawtext, and apply to a clip."""
    client = smoke_client

    # --- Catalog ---
    resp = await client.get("/api/v1/effects")
    assert resp.status_code == 200
    catalog = resp.json()
    assert catalog["total"] > 0

    # Find text_overlay (produces drawtext filter)
    effects_by_type = {e["effect_type"]: e for e in catalog["effects"]}
    assert "text_overlay" in effects_by_type
    text_effect = effects_by_type["text_overlay"]
    assert "parameter_schema" in text_effect
    assert "ai_hints" in text_effect

    # --- Preview ---
    resp = await client.post(
        "/api/v1/effects/preview",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Smoke Test"},
        },
    )
    assert resp.status_code == 200
    preview = resp.json()
    assert "drawtext" in preview["filter_string"]

    # --- Apply to clip ---
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Effects Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    assert resp.status_code == 201
    clip_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Hello World", "fontsize": 48},
        },
    )
    assert resp.status_code == 201
    effect = resp.json()
    assert "drawtext" in effect["filter_string"]
    assert effect["effect_type"] == "text_overlay"


@pytest.mark.usefixtures("videos_dir")
async def test_uc06_effect_update_and_delete(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Update effect parameters and delete an effect from a clip."""
    client = smoke_client

    # Set up project with clip and effect
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Effect Update Project"},
    )
    project_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    clip_id = resp.json()["id"]

    # Apply initial effect
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Original", "fontsize": 24},
        },
    )
    assert resp.status_code == 201
    original_filter = resp.json()["filter_string"]

    # --- Update effect ---
    resp = await client.patch(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects/0",
        json={"parameters": {"text": "Updated", "fontsize": 72}},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["filter_string"] != original_filter
    assert "Updated" in updated["filter_string"] or "drawtext" in updated["filter_string"]

    # --- Delete effect ---
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects/0",
    )
    assert resp.status_code == 200

    # Verify clip has no effects via list endpoint
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    clips = resp.json()["clips"]
    clip = next(c for c in clips if c["id"] == clip_id)
    assert clip["effects"] == []


@pytest.mark.usefixtures("videos_dir")
async def test_uc11_speed_control_and_stacking(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Preview speed effect, apply speed + drawtext stacking on a clip."""
    client = smoke_client

    # --- Preview speed effect ---
    resp = await client.post(
        "/api/v1/effects/preview",
        json={
            "effect_type": "speed_control",
            "parameters": {"factor": 2.0},
        },
    )
    assert resp.status_code == 200
    assert "setpts" in resp.json()["filter_string"].lower()

    # --- Apply stacked effects ---
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Speed Stack Project"},
    )
    project_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 100,
            "timeline_position": 0,
        },
    )
    clip_id = resp.json()["id"]

    # Apply speed_control effect
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "speed_control",
            "parameters": {"factor": 2.0},
        },
    )
    assert resp.status_code == 201

    # Apply drawtext effect (stacking)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Fast Forward"},
        },
    )
    assert resp.status_code == 201

    # Verify clip has 2 effects via list endpoint
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    clips = resp.json()["clips"]
    clip = next(c for c in clips if c["id"] == clip_id)
    assert len(clip["effects"]) == 2
