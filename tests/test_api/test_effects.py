"""Integration tests for effect discovery endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.effects.definitions import (
    SPEED_CONTROL,
    TEXT_OVERLAY,
    EffectDefinition,
    create_default_registry,
)
from stoat_ferret.effects.registry import EffectRegistry

# ---- Registry unit tests ----


@pytest.mark.api
def test_registry_register_and_get() -> None:
    """Registry stores and retrieves effect definitions."""
    registry = EffectRegistry()
    registry.register("text_overlay", TEXT_OVERLAY)

    result = registry.get("text_overlay")
    assert result is TEXT_OVERLAY


@pytest.mark.api
def test_registry_get_unknown_returns_none() -> None:
    """Registry returns None for unregistered effect types."""
    registry = EffectRegistry()
    assert registry.get("nonexistent") is None


@pytest.mark.api
def test_registry_list_all() -> None:
    """Registry lists all registered effects."""
    registry = EffectRegistry()
    registry.register("text_overlay", TEXT_OVERLAY)
    registry.register("speed_control", SPEED_CONTROL)

    items = registry.list_all()
    assert len(items) == 2
    types = [t for t, _ in items]
    assert "text_overlay" in types
    assert "speed_control" in types


@pytest.mark.api
def test_default_registry_has_builtin_effects() -> None:
    """Default registry includes text_overlay and speed_control."""
    registry = create_default_registry()
    items = registry.list_all()
    types = [t for t, _ in items]
    assert "text_overlay" in types
    assert "speed_control" in types


# ---- Endpoint integration tests ----


@pytest.mark.api
def test_list_effects_returns_all_effects(client: TestClient) -> None:
    """GET /effects returns all registered effects."""
    response = client.get("/api/v1/effects")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    types = [e["effect_type"] for e in data["effects"]]
    assert "text_overlay" in types
    assert "speed_control" in types


@pytest.mark.api
def test_effect_includes_name_and_description(client: TestClient) -> None:
    """Each effect includes name and description."""
    response = client.get("/api/v1/effects")
    data = response.json()
    for effect in data["effects"]:
        assert "name" in effect
        assert "description" in effect
        assert len(effect["name"]) > 0
        assert len(effect["description"]) > 0


@pytest.mark.api
def test_effect_includes_parameter_schema(client: TestClient) -> None:
    """Each effect includes a parameter JSON schema."""
    response = client.get("/api/v1/effects")
    data = response.json()
    for effect in data["effects"]:
        schema = effect["parameter_schema"]
        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema


@pytest.mark.api
def test_effect_includes_ai_hints(client: TestClient) -> None:
    """Each effect includes AI hints for parameters."""
    response = client.get("/api/v1/effects")
    data = response.json()
    for effect in data["effects"]:
        hints = effect["ai_hints"]
        assert isinstance(hints, dict)
        assert len(hints) > 0


@pytest.mark.api
def test_effect_includes_filter_preview(client: TestClient) -> None:
    """Each effect includes a Rust-generated filter preview string."""
    response = client.get("/api/v1/effects")
    data = response.json()
    for effect in data["effects"]:
        preview = effect["filter_preview"]
        assert isinstance(preview, str)
        assert len(preview) > 0


@pytest.mark.api
def test_text_overlay_preview_contains_drawtext(client: TestClient) -> None:
    """Text overlay filter preview contains drawtext filter syntax."""
    response = client.get("/api/v1/effects")
    data = response.json()
    text_effect = next(e for e in data["effects"] if e["effect_type"] == "text_overlay")
    assert "drawtext" in text_effect["filter_preview"]


@pytest.mark.api
def test_speed_control_preview_contains_setpts(client: TestClient) -> None:
    """Speed control filter preview contains setpts filter syntax."""
    response = client.get("/api/v1/effects")
    data = response.json()
    speed_effect = next(e for e in data["effects"] if e["effect_type"] == "speed_control")
    assert "setpts" in speed_effect["filter_preview"]


# ---- DI injection tests ----


@pytest.mark.api
def test_injected_registry_used_by_endpoint() -> None:
    """API endpoint uses the injected effect registry."""
    registry = EffectRegistry()
    registry.register(
        "custom_effect",
        EffectDefinition(
            name="Custom",
            description="A custom test effect",
            parameter_schema={"type": "object", "properties": {}},
            ai_hints={"param": "test hint"},
            preview_fn=lambda: "custom_filter=test",
        ),
    )

    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        effect_registry=registry,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/effects")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["effects"][0]["effect_type"] == "custom_effect"
        assert data["effects"][0]["filter_preview"] == "custom_filter=test"


@pytest.mark.api
def test_effect_registry_stored_on_app_state() -> None:
    """create_app() with effect_registry stores it on app.state."""
    registry = EffectRegistry()
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        effect_registry=registry,
    )
    assert app.state.effect_registry is registry


@pytest.mark.api
def test_no_effect_registry_falls_back_to_default() -> None:
    """Without injected registry, endpoint uses default with builtin effects."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/effects")
        assert response.status_code == 200
        data = response.json()
        # Default registry has text_overlay and speed_control
        assert data["total"] == 2
        types = [e["effect_type"] for e in data["effects"]]
        assert "text_overlay" in types
        assert "speed_control" in types
