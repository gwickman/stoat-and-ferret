"""Smoke tests for effects lifecycle (UC-05, UC-06, UC-11).

Validates the deepest stack path: API -> EffectRegistry -> Rust PyO3
filter builders -> filter string generation. Covers effects catalog,
apply/update/delete, speed control with effect stacking, and untested
effect types (audio_ducking, audio_fade, video_fade, acrossfade).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

    # --- Enriched AI-discovery fields (BL-270) ---
    assert "parameters" in text_effect
    assert len(text_effect["parameters"]) > 0
    assert text_effect["ai_summary"]
    assert text_effect["example_prompt"]

    params_by_name = {p["name"]: p for p in text_effect["parameters"]}
    assert "fontsize" in params_by_name
    fontsize = params_by_name["fontsize"]
    assert fontsize["param_type"] == "int"
    assert fontsize["min_value"] is not None
    assert fontsize["max_value"] is not None
    assert fontsize["ai_hint"]

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


# ---------------------------------------------------------------------------
# Effect preview thumbnail tests (BL-086)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("videos_dir")
async def test_effect_preview_thumbnail(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST /effects/preview/thumbnail returns JPEG for a valid effect+video."""
    client = smoke_client

    # Scan videos so we have a real video file
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    assert resp.status_code == 200
    video = resp.json()["videos"][0]
    video_path = video["path"]

    # Request a thumbnail with a text_overlay effect
    resp = await client.post(
        "/api/v1/effects/preview/thumbnail",
        json={
            "effect_name": "text_overlay",
            "video_path": video_path,
            "parameters": {"text": "Smoke Test Thumbnail"},
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    # JPEG files start with the SOI marker
    assert resp.content[:2] == b"\xff\xd8"


@pytest.mark.usefixtures("videos_dir")
async def test_effect_preview_thumbnail_invalid_effect(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST /effects/preview/thumbnail returns 400 for unknown effect."""
    resp = await smoke_client.post(
        "/api/v1/effects/preview/thumbnail",
        json={
            "effect_name": "nonexistent_effect",
            "video_path": "/tmp/fake.mp4",
            "parameters": {},
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Effect type gap-fill tests (BL-146)
# ---------------------------------------------------------------------------


async def _setup_project_with_clip(
    client: httpx.AsyncClient,
    videos_dir: Path,
    project_name: str,
) -> tuple[str, str]:
    """Scan videos, create a project, and add one clip.

    Returns:
        Tuple of (project_id, clip_id).
    """
    await scan_videos_and_wait(client, videos_dir)

    resp = await client.get("/api/v1/videos?limit=1")
    video_id = resp.json()["videos"][0]["id"]

    resp = await client.post(
        "/api/v1/projects",
        json={"name": project_name},
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

    return project_id, clip_id


@pytest.mark.usefixtures("videos_dir")
@pytest.mark.parametrize(
    ("effect_type", "parameters", "filter_keyword"),
    [
        pytest.param(
            "audio_ducking",
            {"threshold": 0.125, "ratio": 2.0, "attack": 20.0, "release": 250.0},
            "sidechaincompress",
            id="audio_ducking",
        ),
        pytest.param(
            "audio_fade",
            {"fade_type": "in", "duration": 1.0},
            "afade",
            id="audio_fade",
        ),
        pytest.param(
            "video_fade",
            {"fade_type": "in", "start_time": 0.0, "duration": 1.0},
            "fade",
            id="video_fade",
        ),
        pytest.param(
            "acrossfade",
            {"duration": 1.0},
            "acrossfade",
            id="acrossfade",
        ),
    ],
)
async def test_create_effect_type(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
    effect_type: str,
    parameters: dict[str, Any],
    filter_keyword: str,
) -> None:
    """Create an effect of the given type and verify 201 with filter string."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, f"Effect Test: {effect_type}"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={"effect_type": effect_type, "parameters": parameters},
    )
    assert resp.status_code == 201
    effect = resp.json()
    assert effect["effect_type"] == effect_type
    assert filter_keyword in effect["filter_string"]

    # Verify effect appears on the clip
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    clips = resp.json()["clips"]
    clip = next(c for c in clips if c["id"] == clip_id)
    assert any(e["effect_type"] == effect_type for e in clip["effects"])
