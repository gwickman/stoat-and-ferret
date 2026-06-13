"""Smoke tests for effects lifecycle (UC-05, UC-06, UC-11).

Validates the deepest stack path: API -> EffectRegistry -> Rust PyO3
filter builders -> filter string generation. Covers effects catalog,
apply/update/delete, speed control with effect stacking, and untested
effect types (audio_ducking, audio_fade, video_fade, acrossfade).
"""

from __future__ import annotations

import os
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
            "effect_type": "text_overlay",
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
            "effect_type": "nonexistent_effect",
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


# ---------------------------------------------------------------------------
# Automation envelope smoke tests (BL-420)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("videos_dir")
async def test_apply_volume_with_automation_envelope(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Valid AutomationEnvelope on volume effect → 201, filter_preview non-null."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Automation Envelope Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "volume",
            "parameters": {
                "volume": {
                    "default": 0.5,
                    "keyframes": [
                        {"t": 0.0, "value": 0.0, "curve": "linear"},
                        {"t": 1.0, "value": 1.0, "curve": "linear"},
                    ],
                }
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filter_preview"] is not None


@pytest.mark.usefixtures("videos_dir")
async def test_apply_volume_with_malformed_envelope(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Non-monotonic keyframe times → 400 (validation error before Rust compiler)."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Malformed Envelope Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "volume",
            "parameters": {
                "volume": {
                    "default": 0.5,
                    "keyframes": [
                        {"t": 1.0, "value": 1.0, "curve": "linear"},
                        {"t": 0.0, "value": 0.0, "curve": "linear"},  # non-monotonic
                    ],
                }
            },
        },
    )
    assert resp.status_code == 400


@pytest.mark.usefixtures("videos_dir")
async def test_apply_volume_scalar_regression(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Scalar parameter path unchanged — 201, filter_preview is None."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Scalar Regression Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "volume",
            "parameters": {"volume": 0.8},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("filter_preview") is None


@pytest.mark.usefixtures("videos_dir")
async def test_apply_non_automatable_with_envelope(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Envelope on a parameter not in the effect's automatable set → 400."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Non-Automatable Envelope Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "volume",
            "parameters": {
                "nonexistent_param": {
                    "default": 0.5,
                    "keyframes": [{"t": 0.0, "value": 0.5, "curve": "linear"}],
                }
            },
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# automatable_parameters smoke tests (BL-481)
# ---------------------------------------------------------------------------


async def test_all_effects_have_automatable_parameters(
    smoke_client: httpx.AsyncClient,
) -> None:
    """All effects returned by GET /effects include a list automatable_parameters field."""
    resp = await smoke_client.get("/api/v1/effects")
    assert resp.status_code == 200
    catalog = resp.json()
    assert catalog["total"] > 0
    for effect in catalog["effects"]:
        assert "automatable_parameters" in effect, (
            f"Effect {effect.get('effect_type')!r} missing automatable_parameters"
        )
        assert isinstance(effect["automatable_parameters"], list), (
            f"Effect {effect.get('effect_type')!r} automatable_parameters is not a list"
        )


# ---------------------------------------------------------------------------
# Preview automation envelope smoke test (BL-482)
# ---------------------------------------------------------------------------


async def test_preview_accepts_automation_envelope(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST /effects/preview with volume + keyframes automation envelope returns 200."""
    resp = await smoke_client.post(
        "/api/v1/effects/preview",
        json={
            "effect_type": "volume",
            "parameters": {
                "volume": {
                    "default": 0.5,
                    "keyframes": [
                        {"t": 0.0, "value": 0.0, "curve": "linear"},
                        {"t": 1.0, "value": 1.0, "curve": "linear"},
                    ],
                }
            },
        },
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Smoke tests for new effect types (v080 Feature 012)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Smoke tests for new v081 video FX effects (BL-454, BL-452, BL-453, BL-455, BL-450)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("videos_dir")
@pytest.mark.parametrize(
    ("effect_type", "parameters", "filter_keyword"),
    [
        pytest.param(
            "blur",
            {"sigma": 2.0},
            "gblur",
            id="blur",
        ),
        pytest.param(
            "sharpen",
            {"amount": 1.0},
            "unsharp",
            id="sharpen",
        ),
        pytest.param(
            "opacity",
            {"opacity": 0.5},
            "colorchannelmixer",
            id="opacity",
        ),
        pytest.param(
            "scale",
            {"scale": 1.5},
            "scale",
            id="scale",
        ),
        pytest.param(
            "color_lut",
            {"preset": "warm_fade"},
            "lut3d",
            id="color_lut",
        ),
        pytest.param(
            "chroma_key",
            {"color": "green", "similarity": 0.1},
            "chromakey",
            id="chroma_key",
        ),
        pytest.param(
            "color_key",
            {"color": "white", "similarity": 0.1},
            "colorkey",
            id="color_key",
        ),
        pytest.param(
            "lens_distort",
            {"k1": 0.1, "k2": 0.05},
            "lenscorrection",
            id="lens_distort",
        ),
    ],
)
async def test_v081_video_fx_effect(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
    effect_type: str,
    parameters: dict[str, Any],
    filter_keyword: str,
) -> None:
    """v081 video FX: effect is in catalog and builds a valid filter string on a clip."""
    client = smoke_client

    # Verify effect is registered in the catalog
    resp = await client.get("/api/v1/effects")
    assert resp.status_code == 200
    effects_by_type = {e["effect_type"]: e for e in resp.json()["effects"]}
    assert effect_type in effects_by_type, (
        f"Effect {effect_type!r} not found in GET /effects catalog"
    )

    # Apply to a real clip and verify 201 + filter keyword
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, f"v081 FX Smoke: {effect_type}"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={"effect_type": effect_type, "parameters": parameters},
    )
    assert resp.status_code == 201, (
        f"Expected 201 for {effect_type!r}, got {resp.status_code}: {resp.text}"
    )
    effect = resp.json()
    assert effect["effect_type"] == effect_type
    assert filter_keyword in effect["filter_string"], (
        f"Expected {filter_keyword!r} in filter_string for {effect_type!r}, "
        f"got: {effect['filter_string']!r}"
    )

    # Verify effect appears on the clip
    resp = await client.get(f"/api/v1/projects/{project_id}/clips")
    assert resp.status_code == 200
    clips = resp.json()["clips"]
    clip = next(c for c in clips if c["id"] == clip_id)
    assert any(e["effect_type"] == effect_type for e in clip["effects"])


@pytest.mark.parametrize(
    ("effect_type", "parameters", "filter_keyword"),
    [
        pytest.param(
            "gradient_generator",
            {"color1": "black", "color2": "white", "duration": 5.0},
            "gradients",
            id="gradient_generator",
        ),
        pytest.param(
            "noise_generator",
            {"duration": 5.0},
            "cellauto",
            id="noise_generator",
        ),
    ],
)
async def test_v081_generator_fx_catalog_and_preview(
    smoke_client: httpx.AsyncClient,
    effect_type: str,
    parameters: dict[str, Any],
    filter_keyword: str,
) -> None:
    """v081 generator FX: effect is in catalog and preview returns a valid filter string."""
    client = smoke_client

    # Verify effect is registered in the catalog
    resp = await client.get("/api/v1/effects")
    assert resp.status_code == 200
    effects_by_type = {e["effect_type"]: e for e in resp.json()["effects"]}
    assert effect_type in effects_by_type, (
        f"Effect {effect_type!r} not found in GET /effects catalog"
    )

    # Verify build via preview endpoint
    resp = await client.post(
        "/api/v1/effects/preview",
        json={"effect_type": effect_type, "parameters": parameters},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for preview of {effect_type!r}, got {resp.status_code}: {resp.text}"
    )
    assert filter_keyword in resp.json()["filter_string"], (
        f"Expected {filter_keyword!r} in filter_string for {effect_type!r}, "
        f"got: {resp.json()['filter_string']!r}"
    )


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.usefixtures("videos_dir")
async def test_smoke_reverse_effect(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Reverse effect smoke test — apply reverse to a clip via API."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Reverse Effect Smoke Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={"effect_type": "reverse", "parameters": {}},
    )
    assert resp.status_code == 201
    effect = resp.json()
    assert effect["effect_type"] == "reverse"
    assert "reverse" in effect["filter_string"].lower()


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.usefixtures("videos_dir")
async def test_smoke_variable_speed_effect(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Variable speed effect smoke test — apply variable speed to a clip."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Variable Speed Effect Smoke Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "variable_speed",
            "parameters": {"segments": [{"start_frame": 0, "end_frame": 100, "speed_factor": 1.5}]},
        },
    )
    assert resp.status_code == 201
    effect = resp.json()
    assert effect["effect_type"] == "variable_speed"


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.usefixtures("videos_dir")
async def test_smoke_framerate_convert_effect(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Framerate convert effect smoke test — apply framerate conversion to a clip."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Framerate Convert Effect Smoke Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "framerate_convert",
            "parameters": {"target_fps": 24.0, "mode": "blend"},
        },
    )
    assert resp.status_code == 201
    effect = resp.json()
    assert effect["effect_type"] == "framerate_convert"


@pytest.mark.skipif(not os.getenv("STOAT_TEST_FFMPEG"), reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.usefixtures("videos_dir")
async def test_smoke_freeze_frame_effect(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """Freeze frame effect smoke test — apply freeze frame to a clip."""
    client = smoke_client
    project_id, clip_id = await _setup_project_with_clip(
        client, videos_dir, "Freeze Frame Effect Smoke Test"
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        json={
            "effect_type": "freeze_frame",
            "parameters": {"frame_number": 0, "duration_s": 2.0},
        },
    )
    assert resp.status_code == 201
    effect = resp.json()
    assert effect["effect_type"] == "freeze_frame"
