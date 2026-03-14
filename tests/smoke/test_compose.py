"""Smoke tests for layout preset discovery and application.

Validates listing compose presets and applying layout presets through the
full HTTP stack with real Rust core providing LayoutPreset data.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from tests.smoke.conftest import scan_videos_and_wait


async def test_compose_list_presets(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/compose/presets returns all 7 layout presets."""
    resp = await smoke_client.get("/api/v1/compose/presets")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total"] == 7
    assert len(body["presets"]) == 7

    # Verify expected preset names are present
    names = {p["name"] for p in body["presets"]}
    expected = {
        "PipTopLeft",
        "PipTopRight",
        "PipBottomLeft",
        "PipBottomRight",
        "SideBySide",
        "TopBottom",
        "Grid2x2",
    }
    assert names == expected

    # Verify each preset has required metadata fields
    for preset in body["presets"]:
        assert "description" in preset
        assert "ai_hint" in preset
        assert isinstance(preset["min_inputs"], int)
        assert isinstance(preset["max_inputs"], int)
        assert preset["min_inputs"] >= 1
        assert preset["max_inputs"] >= preset["min_inputs"]


async def test_compose_layout_apply_preset(
    smoke_client: httpx.AsyncClient,
    videos_dir: Path,
) -> None:
    """POST layout with SideBySide preset returns positions and filter_preview."""
    client = smoke_client

    # Scan videos and create a project to get a valid project_id
    await scan_videos_and_wait(client, videos_dir)
    resp = await client.post("/api/v1/projects", json={"name": "Layout Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Apply SideBySide preset
    resp = await client.post(
        f"/api/v1/projects/{project_id}/compose/layout",
        json={"preset": "SideBySide", "input_count": 2},
    )
    assert resp.status_code == 200

    body = resp.json()

    # Verify positions array with layout coordinates
    assert "positions" in body
    assert isinstance(body["positions"], list)
    assert len(body["positions"]) == 2
    for pos in body["positions"]:
        assert "x" in pos
        assert "y" in pos
        assert "width" in pos
        assert "height" in pos
        assert "z_index" in pos

    # Verify filter_preview contains filter expressions
    assert "filter_preview" in body
    assert isinstance(body["filter_preview"], str)
    assert len(body["filter_preview"]) > 0


async def test_compose_layout_invalid_preset(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST layout with invalid preset name returns 422."""
    client = smoke_client

    # Create a project (layout endpoint requires a project_id in the path)
    resp = await client.post("/api/v1/projects", json={"name": "Invalid Preset Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/compose/layout",
        json={"preset": "NonExistentPreset", "input_count": 2},
    )
    assert resp.status_code == 422

    body = resp.json()
    assert body["detail"]["code"] == "INVALID_REQUEST"
    assert "Unknown preset" in body["detail"]["message"]
