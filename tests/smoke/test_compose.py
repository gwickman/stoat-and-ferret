"""Smoke tests for layout preset discovery.

Validates listing compose presets through the full HTTP stack
with real Rust core providing LayoutPreset data.
"""

from __future__ import annotations

import httpx


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
