"""Integration tests for effect discovery and application endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.effects.definitions import (
    SPEED_CONTROL,
    TEXT_OVERLAY,
    EffectDefinition,
    create_default_registry,
)
from stoat_ferret.effects.registry import EffectRegistry
from tests.factories import make_test_video

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


# ---- Clip effect application tests ----


@pytest.mark.api
async def test_apply_text_overlay_to_clip(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """POST /projects/{id}/clips/{id}/effects applies text overlay and returns filter string."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)
    video = make_test_video()
    await video_repository.add(video)
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    response = client.post(
        "/api/v1/projects/proj-1/clips/clip-1/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Hello World", "fontsize": 48, "fontcolor": "white"},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["effect_type"] == "text_overlay"
    assert "drawtext" in data["filter_string"]
    assert data["parameters"]["text"] == "Hello World"


@pytest.mark.api
async def test_apply_effect_stores_on_clip(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Applied effect is persisted in the clip's effects list."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)
    video = make_test_video()
    await video_repository.add(video)
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    client.post(
        "/api/v1/projects/proj-1/clips/clip-1/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Stored"},
        },
    )

    # Read clip back and verify effects stored
    updated_clip = await clip_repository.get("clip-1")
    assert updated_clip is not None
    assert updated_clip.effects is not None
    assert len(updated_clip.effects) == 1
    assert updated_clip.effects[0]["effect_type"] == "text_overlay"
    assert "drawtext" in updated_clip.effects[0]["filter_string"]


@pytest.mark.api
async def test_apply_effect_unknown_type_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """Applying an unknown effect type returns 400."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id="video-1",
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    response = client.post(
        "/api/v1/projects/proj-1/clips/clip-1/effects",
        json={
            "effect_type": "nonexistent_effect",
            "parameters": {},
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "EFFECT_NOT_FOUND"


@pytest.mark.api
def test_apply_effect_clip_not_found_returns_404(client: TestClient) -> None:
    """Applying effect to nonexistent clip returns 404."""
    response = client.post(
        "/api/v1/projects/proj-1/clips/nonexistent/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Test"},
        },
    )
    assert response.status_code == 404


@pytest.mark.api
async def test_apply_effect_project_not_found_returns_404(
    client: TestClient,
) -> None:
    """Applying effect to clip in nonexistent project returns 404."""
    response = client.post(
        "/api/v1/projects/nonexistent/clips/clip-1/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Test"},
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_apply_effect_filter_string_transparency(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Response includes generated FFmpeg filter string for transparency."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)
    video = make_test_video()
    await video_repository.add(video)
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    response = client.post(
        "/api/v1/projects/proj-1/clips/clip-1/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {
                "text": "Title",
                "fontsize": 64,
                "fontcolor": "yellow",
                "position": "center",
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "filter_string" in data
    assert "drawtext" in data["filter_string"]
    assert "fontsize=64" in data["filter_string"]


@pytest.mark.api
async def test_clip_response_includes_effects(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Clip list response includes applied effects."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-1",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)
    video = make_test_video()
    await video_repository.add(video)
    clip = Clip(
        id="clip-1",
        project_id="proj-1",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    # Apply an effect
    client.post(
        "/api/v1/projects/proj-1/clips/clip-1/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Visible"},
        },
    )

    # List clips and check effects are included
    response = client.get("/api/v1/projects/proj-1/clips")
    assert response.status_code == 200
    data = response.json()
    assert len(data["clips"]) == 1
    clip_data = data["clips"][0]
    assert clip_data["effects"] is not None
    assert len(clip_data["effects"]) == 1
    assert clip_data["effects"][0]["effect_type"] == "text_overlay"
