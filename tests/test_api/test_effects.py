"""Integration tests for effect discovery and application endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.routers.effects import effect_applications_total
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.effects.definitions import (
    ACROSSFADE,
    AUDIO_DUCKING,
    AUDIO_FADE,
    AUDIO_MIX,
    SPEED_CONTROL,
    TEXT_OVERLAY,
    VIDEO_FADE,
    VOLUME,
    XFADE,
    EffectDefinition,
    _build_speed_control,
    _build_text_overlay,
    create_default_registry,
)
from stoat_ferret.effects.registry import EffectRegistry
from tests.factories import make_test_video

#: All effect types that must be registered in the default registry.
EXPECTED_EFFECT_TYPES = {
    "text_overlay",
    "speed_control",
    "audio_mix",
    "volume",
    "audio_fade",
    "audio_ducking",
    "video_fade",
    "xfade",
    "acrossfade",
}

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
            build_fn=lambda params: "custom_filter=test",
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
        # Default registry has all built-in effects
        assert data["total"] == len(EXPECTED_EFFECT_TYPES)
        types = {e["effect_type"] for e in data["effects"]}
        assert types == EXPECTED_EFFECT_TYPES


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


# ---- Parity tests: build_fn produces same output as old dispatch ----


@pytest.mark.api
def test_parity_text_overlay_build_fn() -> None:
    """build_fn for text_overlay produces identical output to old dispatch."""
    params: dict[str, Any] = {
        "text": "Hello World",
        "fontsize": 48,
        "fontcolor": "white",
        "position": "bottom_center",
        "margin": 20,
    }
    result = _build_text_overlay(params)
    assert "drawtext" in result
    assert "Hello World" in result or "Hello" in result
    assert "fontsize=48" in result
    assert "fontcolor=white" in result


@pytest.mark.api
def test_parity_speed_control_build_fn() -> None:
    """build_fn for speed_control produces identical output to old dispatch."""
    params: dict[str, Any] = {"factor": 2.0}
    result = _build_speed_control(params)
    assert "setpts" in result
    assert "atempo" in result


# ---- EffectDefinition build_fn callable invocation tests ----


@pytest.mark.api
def test_effect_definition_build_fn_callable() -> None:
    """EffectDefinition.build_fn is callable and returns a string."""
    result = TEXT_OVERLAY.build_fn({"text": "Test"})
    assert isinstance(result, str)
    assert "drawtext" in result


@pytest.mark.api
def test_effect_definition_build_fn_receives_params() -> None:
    """EffectDefinition.build_fn receives parameter dict correctly."""
    result = SPEED_CONTROL.build_fn({"factor": 0.5})
    assert isinstance(result, str)
    assert "setpts" in result


@pytest.mark.api
def test_effect_definition_build_fn_returns_filter_string() -> None:
    """Each built-in effect's build_fn returns a non-empty string."""
    effects_and_params: list[tuple[EffectDefinition, dict[str, Any]]] = [
        (TEXT_OVERLAY, {"text": "test"}),
        (SPEED_CONTROL, {"factor": 2.0}),
        (AUDIO_MIX, {"inputs": 2}),
        (VOLUME, {"volume": 1.5}),
        (AUDIO_FADE, {"fade_type": "in", "duration": 1.0}),
        (AUDIO_DUCKING, {}),
        (VIDEO_FADE, {"fade_type": "in", "duration": 1.0}),
        (XFADE, {"transition": "fade", "duration": 1.0, "offset": 0.0}),
        (ACROSSFADE, {"duration": 1.0}),
    ]
    for defn, params in effects_and_params:
        result = defn.build_fn(params)
        assert isinstance(result, str), f"{defn.name} build_fn did not return str"
        assert len(result) > 0, f"{defn.name} build_fn returned empty string"


# ---- JSON schema validation tests ----


@pytest.mark.api
def test_schema_validation_valid_params() -> None:
    """Valid parameters pass schema validation with no errors."""
    registry = create_default_registry()
    errors = registry.validate("text_overlay", {"text": "Hello"})
    assert errors == []


@pytest.mark.api
def test_schema_validation_missing_required_field() -> None:
    """Missing required field is detected by schema validation."""
    registry = create_default_registry()
    errors = registry.validate("text_overlay", {})
    assert len(errors) > 0
    messages = [e.message for e in errors]
    assert any("text" in m and "required" in m.lower() for m in messages)


@pytest.mark.api
def test_schema_validation_type_mismatch() -> None:
    """Type mismatch is detected by schema validation."""
    registry = create_default_registry()
    errors = registry.validate("text_overlay", {"text": "Hello", "fontsize": "not_a_number"})
    assert len(errors) > 0
    assert any("fontsize" in e.path for e in errors)


@pytest.mark.api
def test_schema_validation_invalid_enum_value() -> None:
    """Invalid enum value is detected by schema validation."""
    registry = create_default_registry()
    errors = registry.validate("text_overlay", {"text": "Hello", "position": "invalid_position"})
    assert len(errors) > 0


@pytest.mark.api
def test_schema_validation_unknown_effect_raises_keyerror() -> None:
    """Validating an unknown effect type raises KeyError."""
    registry = create_default_registry()
    with pytest.raises(KeyError, match="Unknown effect type"):
        registry.validate("nonexistent", {})


# ---- Registry dispatch tests ----


@pytest.mark.api
def test_registry_dispatch_text_overlay() -> None:
    """Registry dispatch for text_overlay produces drawtext filter."""
    registry = create_default_registry()
    defn = registry.get("text_overlay")
    assert defn is not None
    result = defn.build_fn({"text": "dispatch test"})
    assert "drawtext" in result


@pytest.mark.api
def test_registry_dispatch_speed_control() -> None:
    """Registry dispatch for speed_control produces setpts filter."""
    registry = create_default_registry()
    defn = registry.get("speed_control")
    assert defn is not None
    result = defn.build_fn({"factor": 1.5})
    assert "setpts" in result


@pytest.mark.api
def test_registry_dispatch_volume() -> None:
    """Registry dispatch for volume produces volume filter."""
    registry = create_default_registry()
    defn = registry.get("volume")
    assert defn is not None
    result = defn.build_fn({"volume": 2.0})
    assert "volume" in result


@pytest.mark.api
def test_registry_dispatch_video_fade() -> None:
    """Registry dispatch for video_fade produces fade filter."""
    registry = create_default_registry()
    defn = registry.get("video_fade")
    assert defn is not None
    result = defn.build_fn({"fade_type": "in", "duration": 1.0})
    assert "fade" in result


# ---- Registration completeness test ----


@pytest.mark.api
def test_registry_completeness() -> None:
    """Default registry contains all expected effect types."""
    registry = create_default_registry()
    registered_types = {t for t, _ in registry.list_all()}
    assert registered_types == EXPECTED_EFFECT_TYPES


# ---- EffectDefinition schema round-trip contract test ----


@pytest.mark.contract
def test_effect_definition_schema_roundtrip() -> None:
    """EffectDefinition parameter_schema validates its own build_fn default params."""
    # Each effect's schema should accept the parameters used in its preview
    registry = create_default_registry()
    # text_overlay: preview uses default params, build_fn uses {"text": "x"}
    errors = registry.validate("text_overlay", {"text": "test"})
    assert errors == [], f"text_overlay schema rejected valid params: {errors}"

    errors = registry.validate("speed_control", {"factor": 2.0})
    assert errors == [], f"speed_control schema rejected valid params: {errors}"


# ---- Prometheus metrics tests ----


@pytest.mark.api
async def test_prometheus_counter_increments_on_apply(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Prometheus counter increments when an effect is applied."""
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

    # Record counter before
    before = effect_applications_total.labels(effect_type="text_overlay")._value.get()

    response = client.post(
        "/api/v1/projects/proj-1/clips/clip-1/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"text": "Metrics Test"},
        },
    )
    assert response.status_code == 201

    # Counter should have incremented
    after = effect_applications_total.labels(effect_type="text_overlay")._value.get()
    assert after == before + 1


@pytest.mark.api
def test_prometheus_counter_exists() -> None:
    """The effect applications counter is registered with correct name."""
    # prometheus_client strips _total suffix from counter _name
    assert effect_applications_total._name == "stoat_ferret_effect_applications"


# ---- Schema validation via API endpoint tests ----


@pytest.mark.api
async def test_apply_effect_with_invalid_params_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Applying effect with schema-invalid parameters returns 400."""
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

    # Missing required 'text' field
    response = client.post(
        "/api/v1/projects/proj-1/clips/clip-1/effects",
        json={
            "effect_type": "text_overlay",
            "parameters": {"fontsize": 48},
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "INVALID_EFFECT_PARAMS"


# ---- TransitionRequest/TransitionResponse schema contract tests ----


@pytest.mark.contract
def test_transition_request_schema_roundtrip() -> None:
    """TransitionRequest serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.effect import TransitionRequest

    data = {
        "source_clip_id": "clip-a",
        "target_clip_id": "clip-b",
        "transition_type": "xfade",
        "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
    }
    req = TransitionRequest(**data)
    assert req.source_clip_id == "clip-a"
    assert req.target_clip_id == "clip-b"
    assert req.transition_type == "xfade"
    assert req.parameters["transition"] == "fade"

    # Round-trip via dict
    dumped = req.model_dump()
    restored = TransitionRequest(**dumped)
    assert restored == req


@pytest.mark.contract
def test_transition_response_schema_roundtrip() -> None:
    """TransitionResponse serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.effect import TransitionResponse

    data = {
        "source_clip_id": "clip-a",
        "target_clip_id": "clip-b",
        "transition_type": "xfade",
        "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        "filter_string": "xfade=transition=fade:duration=1:offset=0",
    }
    resp = TransitionResponse(**data)
    assert resp.filter_string == "xfade=transition=fade:duration=1:offset=0"

    dumped = resp.model_dump()
    restored = TransitionResponse(**dumped)
    assert restored == resp


# ---- Clip adjacency validation tests ----


async def _seed_project_with_clips(
    project_repo: AsyncInMemoryProjectRepository,
    clip_repo: AsyncInMemoryClipRepository,
    video_repo: AsyncInMemoryVideoRepository,
    clip_count: int = 2,
) -> tuple[str, list[str]]:
    """Seed a project with adjacent clips for transition testing.

    Args:
        project_repo: Project repository to seed.
        clip_repo: Clip repository to seed.
        video_repo: Video repository to seed.
        clip_count: Number of clips to create.

    Returns:
        Tuple of (project_id, list of clip_ids in timeline order).
    """
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-t",
        name="Transition Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repo.add(project)

    clip_ids: list[str] = []
    for i in range(clip_count):
        video = make_test_video()
        await video_repo.add(video)
        clip_id = f"clip-{i}"
        clip = Clip(
            id=clip_id,
            project_id="proj-t",
            source_video_id=video.id,
            in_point=0,
            out_point=100,
            timeline_position=i * 100,
            created_at=now,
            updated_at=now,
        )
        await clip_repo.add(clip)
        clip_ids.append(clip_id)

    return "proj-t", clip_ids


@pytest.mark.api
async def test_transition_adjacent_clips_succeeds(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """POST /effects/transition succeeds for adjacent clips."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[1],
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_clip_id"] == clip_ids[0]
    assert data["target_clip_id"] == clip_ids[1]
    assert data["transition_type"] == "xfade"
    assert "filter_string" in data
    assert len(data["filter_string"]) > 0


@pytest.mark.api
async def test_transition_non_adjacent_clips_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """POST /effects/transition returns 400 for non-adjacent clips."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository, clip_count=3
    )

    # clip-0 and clip-2 are not adjacent (clip-1 is between them)
    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[2],
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "NOT_ADJACENT"


@pytest.mark.api
async def test_transition_same_clip_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """POST /effects/transition returns 400 when source equals target."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[0],
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "SAME_CLIP"


@pytest.mark.api
async def test_transition_empty_timeline_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """POST /effects/transition returns 400 for empty timeline."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-empty",
        name="Empty",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    response = client.post(
        "/api/v1/projects/proj-empty/effects/transition",
        json={
            "source_clip_id": "clip-x",
            "target_clip_id": "clip-y",
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "EMPTY_TIMELINE"


@pytest.mark.api
async def test_transition_nonexistent_clip_returns_404(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """POST /effects/transition returns 404 for nonexistent clip IDs."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": "nonexistent",
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_transition_nonexistent_project_returns_404(
    client: TestClient,
) -> None:
    """POST /effects/transition returns 404 for nonexistent project."""
    response = client.post(
        "/api/v1/projects/nonexistent/effects/transition",
        json={
            "source_clip_id": "clip-a",
            "target_clip_id": "clip-b",
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "NOT_FOUND"


# ---- Transition parameter validation tests ----


@pytest.mark.api
async def test_transition_unknown_type_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """POST /effects/transition returns 400 for unknown transition type."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[1],
            "transition_type": "nonexistent_type",
            "parameters": {},
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "EFFECT_NOT_FOUND"


@pytest.mark.api
async def test_transition_invalid_params_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """POST /effects/transition returns 400 for invalid parameters."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    # xfade requires transition, duration, offset
    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[1],
            "transition_type": "xfade",
            "parameters": {},
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "INVALID_EFFECT_PARAMS"


# ---- Transition storage tests ----


@pytest.mark.api
async def test_transition_stored_in_project(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Applied transition is stored in the project's transitions list."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[1],
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )

    updated_project = await project_repository.get(project_id)
    assert updated_project is not None
    assert updated_project.transitions is not None
    assert len(updated_project.transitions) == 1
    t = updated_project.transitions[0]
    assert t["source_clip_id"] == clip_ids[0]
    assert t["target_clip_id"] == clip_ids[1]
    assert t["transition_type"] == "xfade"
    assert "filter_string" in t
    assert len(t["filter_string"]) > 0


@pytest.mark.api
async def test_transition_persists_after_retrieval(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Stored transition is retrievable from the project."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[1],
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 201
    response_data = response.json()

    # Retrieve again and verify persistence
    project = await project_repository.get(project_id)
    assert project is not None
    assert project.transitions is not None
    assert project.transitions[0]["filter_string"] == response_data["filter_string"]


# ---- Transition response transparency test ----


@pytest.mark.api
async def test_transition_response_includes_filter_string(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Transition response includes generated FFmpeg filter string."""
    project_id, clip_ids = await _seed_project_with_clips(
        project_repository, clip_repository, video_repository
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/effects/transition",
        json={
            "source_clip_id": clip_ids[0],
            "target_clip_id": clip_ids[1],
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "filter_string" in data
    assert "xfade" in data["filter_string"]
    assert data["transition_type"] == "xfade"
    assert data["parameters"]["transition"] == "fade"


# ---- Black-box test: full transition flow ----


@pytest.mark.api
async def test_transition_black_box_full_flow(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Full flow: create project, add clips, apply transition, verify response."""
    # 1. Create project
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-bb",
        name="Black Box Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    # 2. Add two adjacent clips
    video1 = make_test_video()
    video2 = make_test_video()
    await video_repository.add(video1)
    await video_repository.add(video2)

    clip1 = Clip(
        id="bb-clip-1",
        project_id="proj-bb",
        source_video_id=video1.id,
        in_point=0,
        out_point=150,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    clip2 = Clip(
        id="bb-clip-2",
        project_id="proj-bb",
        source_video_id=video2.id,
        in_point=0,
        out_point=200,
        timeline_position=150,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip1)
    await clip_repository.add(clip2)

    # 3. Apply transition
    response = client.post(
        "/api/v1/projects/proj-bb/effects/transition",
        json={
            "source_clip_id": "bb-clip-1",
            "target_clip_id": "bb-clip-2",
            "transition_type": "xfade",
            "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        },
    )

    # 4. Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["source_clip_id"] == "bb-clip-1"
    assert data["target_clip_id"] == "bb-clip-2"
    assert data["transition_type"] == "xfade"
    assert "xfade" in data["filter_string"]
    assert data["parameters"]["transition"] == "fade"
    assert data["parameters"]["duration"] == 1.0

    # 5. Verify persistent storage
    project = await project_repository.get("proj-bb")
    assert project is not None
    assert project.transitions is not None
    assert len(project.transitions) == 1
    stored = project.transitions[0]
    assert stored["filter_string"] == data["filter_string"]
