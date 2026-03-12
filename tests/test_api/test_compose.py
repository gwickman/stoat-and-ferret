"""Tests for compose layout preset discovery and application endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret_core import LayoutPreset, build_overlay_filter

#: All 7 layout preset names that must be returned.
EXPECTED_PRESET_NAMES = {
    "PipTopLeft",
    "PipTopRight",
    "PipBottomLeft",
    "PipBottomRight",
    "SideBySide",
    "TopBottom",
    "Grid2x2",
}

#: Required metadata fields on each preset response.
REQUIRED_FIELDS = {"name", "description", "ai_hint", "min_inputs", "max_inputs"}


# ---- Endpoint integration tests ----


@pytest.mark.api
def test_list_presets_returns_200(client: TestClient) -> None:
    """GET /compose/presets returns 200."""
    response = client.get("/api/v1/compose/presets")
    assert response.status_code == 200


@pytest.mark.api
def test_list_presets_returns_seven_presets(client: TestClient) -> None:
    """GET /compose/presets returns exactly 7 presets."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    assert data["total"] == 7
    assert len(data["presets"]) == 7


@pytest.mark.api
def test_list_presets_contains_all_preset_names(client: TestClient) -> None:
    """All 7 expected preset names are present in the response."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    names = {p["name"] for p in data["presets"]}
    assert names == EXPECTED_PRESET_NAMES


@pytest.mark.api
def test_preset_includes_all_metadata_fields(client: TestClient) -> None:
    """Each preset includes name, description, ai_hint, min_inputs, max_inputs."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    for preset in data["presets"]:
        assert set(preset.keys()) >= REQUIRED_FIELDS, (
            f"Preset {preset.get('name')} missing fields: {REQUIRED_FIELDS - set(preset.keys())}"
        )


@pytest.mark.api
def test_preset_descriptions_are_non_empty(client: TestClient) -> None:
    """All preset descriptions are non-empty strings."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    for preset in data["presets"]:
        assert isinstance(preset["description"], str)
        assert len(preset["description"]) > 0


@pytest.mark.api
def test_preset_ai_hints_are_non_empty(client: TestClient) -> None:
    """All preset ai_hints are non-empty strings."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    for preset in data["presets"]:
        assert isinstance(preset["ai_hint"], str)
        assert len(preset["ai_hint"]) > 0


@pytest.mark.api
def test_preset_input_counts_are_positive(client: TestClient) -> None:
    """All preset min_inputs and max_inputs are positive integers."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    for preset in data["presets"]:
        assert isinstance(preset["min_inputs"], int)
        assert isinstance(preset["max_inputs"], int)
        assert preset["min_inputs"] > 0
        assert preset["max_inputs"] >= preset["min_inputs"]


@pytest.mark.api
def test_pip_presets_require_two_inputs(client: TestClient) -> None:
    """PIP presets require exactly 2 inputs."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    pip_presets = [p for p in data["presets"] if p["name"].startswith("Pip")]
    assert len(pip_presets) == 4
    for preset in pip_presets:
        assert preset["min_inputs"] == 2
        assert preset["max_inputs"] == 2


@pytest.mark.api
def test_grid_preset_requires_four_inputs(client: TestClient) -> None:
    """Grid2x2 preset requires exactly 4 inputs."""
    response = client.get("/api/v1/compose/presets")
    data = response.json()
    grid = next(p for p in data["presets"] if p["name"] == "Grid2x2")
    assert grid["min_inputs"] == 4
    assert grid["max_inputs"] == 4


@pytest.mark.api
def test_endpoint_accessible_without_auth(client: TestClient) -> None:
    """Endpoint returns 200 without any auth headers (NFR-001)."""
    response = client.get("/api/v1/compose/presets")
    assert response.status_code == 200


# ---- Parity test: preset count matches Rust enum ----


@pytest.mark.api
def test_preset_count_matches_rust_enum() -> None:
    """Python preset metadata covers all Rust LayoutPreset variants."""
    from stoat_ferret.api.routers.compose import _PRESET_METADATA
    from stoat_ferret_core import LayoutPreset

    rust_variants = [
        LayoutPreset.PipTopLeft,
        LayoutPreset.PipTopRight,
        LayoutPreset.PipBottomLeft,
        LayoutPreset.PipBottomRight,
        LayoutPreset.SideBySide,
        LayoutPreset.TopBottom,
        LayoutPreset.Grid2x2,
    ]
    metadata_variants = [v for v, _ in _PRESET_METADATA]
    assert len(metadata_variants) == len(rust_variants)
    for variant in rust_variants:
        assert variant in metadata_variants, f"Missing metadata for {variant!r}"


# ---- DTO round-trip test ----


@pytest.mark.api
def test_layout_preset_response_round_trip() -> None:
    """LayoutPresetResponse serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.compose import LayoutPresetResponse

    preset = LayoutPresetResponse(
        name="SideBySide",
        description="Two inputs side by side",
        ai_hint="Use for comparisons",
        min_inputs=2,
        max_inputs=2,
    )
    data = preset.model_dump()
    restored = LayoutPresetResponse.model_validate(data)
    assert restored == preset


# ---- Layout application endpoint tests ----

LAYOUT_URL = "/api/v1/projects/test-project/compose/layout"


@pytest.mark.api
def test_apply_layout_preset_returns_200(client: TestClient) -> None:
    """POST layout with preset name returns 200."""
    response = client.post(LAYOUT_URL, json={"preset": "PipTopLeft"})
    assert response.status_code == 200


@pytest.mark.api
def test_apply_layout_preset_returns_positions(client: TestClient) -> None:
    """POST layout with preset returns correct number of positions."""
    response = client.post(LAYOUT_URL, json={"preset": "PipTopLeft"})
    data = response.json()
    assert len(data["positions"]) == 2


@pytest.mark.api
def test_apply_layout_preset_returns_filter_preview(client: TestClient) -> None:
    """POST layout with preset returns non-empty filter_preview."""
    response = client.post(LAYOUT_URL, json={"preset": "PipTopLeft"})
    data = response.json()
    assert isinstance(data["filter_preview"], str)
    assert len(data["filter_preview"]) > 0
    assert "overlay" in data["filter_preview"]


@pytest.mark.api
def test_apply_layout_preset_pip_positions(client: TestClient) -> None:
    """PipTopLeft preset returns full-screen base and small overlay."""
    response = client.post(LAYOUT_URL, json={"preset": "PipTopLeft"})
    data = response.json()
    positions = data["positions"]
    # Base layer: full screen at z_index 0
    assert positions[0]["x"] == 0.0
    assert positions[0]["y"] == 0.0
    assert positions[0]["width"] == 1.0
    assert positions[0]["height"] == 1.0
    assert positions[0]["z_index"] == 0
    # Overlay: smaller, z_index 1
    assert positions[1]["z_index"] == 1
    assert positions[1]["width"] < 1.0
    assert positions[1]["height"] < 1.0


@pytest.mark.api
def test_apply_layout_grid2x2_returns_four_positions(client: TestClient) -> None:
    """Grid2x2 preset returns 4 positions."""
    response = client.post(LAYOUT_URL, json={"preset": "Grid2x2", "input_count": 4})
    data = response.json()
    assert len(data["positions"]) == 4


@pytest.mark.api
def test_apply_layout_side_by_side(client: TestClient) -> None:
    """SideBySide preset returns two half-width positions."""
    response = client.post(LAYOUT_URL, json={"preset": "SideBySide"})
    data = response.json()
    positions = data["positions"]
    assert len(positions) == 2
    assert positions[0]["width"] == 0.5
    assert positions[1]["width"] == 0.5


@pytest.mark.api
def test_apply_layout_custom_positions_returns_200(client: TestClient) -> None:
    """POST layout with custom positions returns 200."""
    response = client.post(
        LAYOUT_URL,
        json={
            "positions": [
                {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5},
                {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5},
            ]
        },
    )
    assert response.status_code == 200


@pytest.mark.api
def test_apply_layout_custom_positions_reflected(client: TestClient) -> None:
    """Custom positions are reflected in the response."""
    custom = [
        {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
    ]
    response = client.post(LAYOUT_URL, json={"positions": custom})
    data = response.json()
    assert len(data["positions"]) == 1
    pos = data["positions"][0]
    assert pos["x"] == pytest.approx(0.1)
    assert pos["y"] == pytest.approx(0.2)
    assert pos["width"] == pytest.approx(0.3)
    assert pos["height"] == pytest.approx(0.4)


@pytest.mark.api
def test_apply_layout_custom_positions_filter_preview(client: TestClient) -> None:
    """Custom positions generate filter_preview with overlay syntax."""
    response = client.post(
        LAYOUT_URL,
        json={
            "positions": [
                {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                {"x": 0.5, "y": 0.5, "width": 0.25, "height": 0.25},
            ]
        },
    )
    data = response.json()
    assert "overlay" in data["filter_preview"]


@pytest.mark.api
def test_apply_layout_invalid_position_returns_422(client: TestClient) -> None:
    """Out-of-range coordinates return 422 with INVALID_LAYOUT_POSITION."""
    response = client.post(
        LAYOUT_URL,
        json={
            "positions": [
                {"x": 1.5, "y": 0.0, "width": 0.5, "height": 0.5},
            ]
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_LAYOUT_POSITION"


@pytest.mark.api
def test_apply_layout_negative_position_returns_422(client: TestClient) -> None:
    """Negative coordinates return 422 with INVALID_LAYOUT_POSITION."""
    response = client.post(
        LAYOUT_URL,
        json={
            "positions": [
                {"x": -0.1, "y": 0.0, "width": 0.5, "height": 0.5},
            ]
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_LAYOUT_POSITION"


@pytest.mark.api
def test_apply_layout_insufficient_inputs_returns_422(client: TestClient) -> None:
    """Grid2x2 with fewer than 4 inputs returns 422 INSUFFICIENT_INPUTS."""
    response = client.post(
        LAYOUT_URL,
        json={"preset": "Grid2x2", "input_count": 2},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INSUFFICIENT_INPUTS"


@pytest.mark.api
def test_apply_layout_unknown_preset_returns_422(client: TestClient) -> None:
    """Unknown preset name returns 422."""
    response = client.post(LAYOUT_URL, json={"preset": "NonExistent"})
    assert response.status_code == 422


@pytest.mark.api
def test_apply_layout_neither_preset_nor_positions_returns_422(
    client: TestClient,
) -> None:
    """Request with neither preset nor positions returns 422."""
    response = client.post(LAYOUT_URL, json={})
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["code"] == "INVALID_REQUEST"


@pytest.mark.api
def test_apply_layout_custom_output_dimensions(client: TestClient) -> None:
    """Custom output dimensions affect the filter preview."""
    response = client.post(
        LAYOUT_URL,
        json={
            "preset": "PipTopLeft",
            "output_width": 3840,
            "output_height": 2160,
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert "overlay" in data["filter_preview"]


# ---- Parity: filter preview matches direct Rust call ----


@pytest.mark.api
def test_filter_preview_matches_rust_build_overlay_filter() -> None:
    """Filter preview output matches direct Rust build_overlay_filter() call."""
    preset = LayoutPreset.PipTopLeft
    positions = preset.positions(2)
    expected_filters = [build_overlay_filter(pos, 1920, 1080, 0.0, 10.0) for pos in positions]
    expected_preview = ";".join(expected_filters)

    from stoat_ferret.api.routers.compose import _resolve_preset

    resolved = _resolve_preset("PipTopLeft", 2)
    actual_filters = [build_overlay_filter(pos, 1920, 1080, 0.0, 10.0) for pos in resolved]
    actual_preview = ";".join(actual_filters)
    assert actual_preview == expected_preview


# ---- DTO round-trip tests for new schemas ----


@pytest.mark.api
def test_layout_request_round_trip() -> None:
    """LayoutRequest serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.compose import LayoutRequest

    req = LayoutRequest(preset="PipTopLeft", input_count=2)
    data = req.model_dump()
    restored = LayoutRequest.model_validate(data)
    assert restored == req


@pytest.mark.api
def test_layout_response_round_trip() -> None:
    """LayoutResponse serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.compose import LayoutResponse, LayoutResponsePosition

    resp = LayoutResponse(
        positions=[LayoutResponsePosition(x=0.0, y=0.0, width=1.0, height=1.0, z_index=0)],
        filter_preview="overlay=x=0:y=0:enable='between(t,0,10)'",
    )
    data = resp.model_dump()
    restored = LayoutResponse.model_validate(data)
    assert restored == resp


# ---- Broadcast wiring tests ----


@pytest.mark.api
def test_apply_layout_broadcasts_layout_applied(app: FastAPI, client: TestClient) -> None:
    """POST layout broadcasts layout_applied event via ws_manager."""
    mock_manager = AsyncMock(spec=ConnectionManager)
    app.state.ws_manager = mock_manager

    client.post(LAYOUT_URL, json={"preset": "PipTopLeft"})

    mock_manager.broadcast.assert_awaited_once()
    event = mock_manager.broadcast.call_args[0][0]
    assert event["type"] == "layout_applied"
    assert event["payload"]["project_id"] == "test-project"
    assert event["payload"]["preset"] == "PipTopLeft"


@pytest.mark.api
def test_apply_layout_no_broadcast_without_ws_manager(app: FastAPI, client: TestClient) -> None:
    """POST layout does not fail when ws_manager is not available."""
    # Ensure no ws_manager is set
    if hasattr(app.state, "ws_manager"):
        delattr(app.state, "ws_manager")

    response = client.post(LAYOUT_URL, json={"preset": "PipTopLeft"})
    assert response.status_code == 200
