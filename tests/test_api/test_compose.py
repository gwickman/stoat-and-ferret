"""Tests for compose layout preset discovery endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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
