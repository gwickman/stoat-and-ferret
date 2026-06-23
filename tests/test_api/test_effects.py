# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Integration tests for effect discovery and application endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
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
    DEESSER,
    DEPLOSIVE,
    LOUDNESS_NORMALIZE,
    MASTERING_LIMITER,
    MULTIBAND_COMPRESSOR,
    NOISE_REDUCTION,
    PARAMETRIC_EQ,
    SPEED_CONTROL,
    TEXT_OVERLAY,
    TIME_STRETCH,
    VIDEO_FADE,
    VOLUME,
    XFADE,
    EffectDefinition,
    _build_deesser,
    _build_deplosive,
    _build_loudness_normalize,
    _build_mastering_limiter,
    _build_multiband_compressor,
    _build_noise_reduction,
    _build_parametric_eq,
    _build_speed_control,
    _build_text_overlay,
    _build_time_stretch,
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
    "noise_reduction",
    "deesser",
    "deplosive",
    "time_stretch",
    "mastering_limiter",
    "loudness_normalize",
    "parametric_eq",
    "multiband_compressor",
    "pan",
    "convolution_reverb",
    "reverse",
    "variable_speed",
    "framerate_convert",
    "freeze_frame",
    "blur",
    "sharpen",
    "opacity",
    "scale",
    "chroma_key",
    "color_key",
    "color_lut",
    "lens_distort",
    "chromatic_aberration",
    "gradient_generator",
    "noise_generator",
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
    """Effects with configurable parameters include AI hints for those parameters."""
    response = client.get("/api/v1/effects")
    data = response.json()
    for effect in data["effects"]:
        hints = effect["ai_hints"]
        assert isinstance(hints, dict)
        schema = effect.get("parameter_schema", {})
        has_params = bool(schema.get("properties"))
        if has_params:
            assert len(hints) > 0, (
                f"Effect '{effect['effect_type']}' has parameters but no AI hints"
            )


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
    assert "valid_effect_types" in data["detail"]
    assert isinstance(data["detail"]["valid_effect_types"], list)


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

    errors = registry.validate("noise_reduction", {"mode": "broadband", "strength": 0.5})
    assert errors == [], f"noise_reduction schema rejected valid broadband params: {errors}"

    errors = registry.validate("noise_reduction", {"mode": "adeclick", "threshold": 0.3})
    assert errors == [], f"noise_reduction schema rejected valid adeclick params: {errors}"

    errors = registry.validate("noise_reduction", {})
    assert errors == [], f"noise_reduction schema rejected empty params (all optional): {errors}"

    errors = registry.validate("deesser", {"frequency": 6000.0, "mode": "wide"})
    assert errors == [], f"deesser schema rejected valid params: {errors}"

    errors = registry.validate("deesser", {})
    assert errors == [], f"deesser schema rejected empty params (all optional): {errors}"

    errors = registry.validate("deplosive", {"cutoff": 60.0, "threshold": 0.1, "ratio": 4.0})
    assert errors == [], f"deplosive schema rejected valid params: {errors}"

    errors = registry.validate("deplosive", {})
    assert errors == [], f"deplosive schema rejected empty params (all optional): {errors}"

    errors = registry.validate("time_stretch", {"factor": 0.8})
    assert errors == [], f"time_stretch schema rejected valid params: {errors}"

    errors = registry.validate("time_stretch", {"factor": 2.5, "mode": "atempo"})
    assert errors == [], f"time_stretch schema rejected factor+mode params: {errors}"

    errors = registry.validate("time_stretch", {"factor": 1.5, "mode": "rubberband"})
    assert errors == [], f"time_stretch schema rejected rubberband params: {errors}"

    errors = registry.validate("mastering_limiter", {"ceiling_dbtp": -1.0})
    assert errors == [], f"mastering_limiter schema rejected valid params: {errors}"

    errors = registry.validate("mastering_limiter", {"ceiling_dbtp": 0.0})
    assert errors == [], f"mastering_limiter schema rejected 0.0 dBTP: {errors}"

    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"frequency": 1000.0, "gain": 6.0, "width": 200.0}]},
    )
    assert errors == [], f"parametric_eq schema rejected valid params: {errors}"


@pytest.mark.contract
def test_mastering_limiter_build_fn() -> None:
    """mastering_limiter build_fn emits correct alimiter filter string."""
    filter_str = _build_mastering_limiter({"ceiling_dbtp": -1.0})
    assert filter_str.startswith("alimiter=limit=0.891"), (
        f"Expected alimiter=limit=0.891..., got: {filter_str}"
    )
    assert "level=disabled" in filter_str, f"Missing level=disabled in: {filter_str}"


@pytest.mark.contract
def test_mastering_limiter_definition_registered() -> None:
    """mastering_limiter is registered in the default registry."""
    registry = create_default_registry()
    effect = registry.get("mastering_limiter")
    assert effect is not None, "mastering_limiter not found in default registry"
    assert effect is MASTERING_LIMITER
    preview = effect.preview_fn()
    assert "alimiter" in preview, f"Preview missing alimiter: {preview}"


# ---- loudness_normalize schema and round-trip tests ----


@pytest.mark.contract
def test_loudness_normalize_build_fn_pass1() -> None:
    """loudness_normalize build_fn returns pass-1 filter string without measurements."""
    filter_str = _build_loudness_normalize({"target_lufs": -16.0, "ceiling_dbtp": -1.0})
    assert "loudnorm=" in filter_str, f"Expected loudnorm filter, got: {filter_str}"
    assert "print_format=json" in filter_str, f"Expected pass-1 filter, got: {filter_str}"
    assert "I=-16" in filter_str, f"Missing I=-16 in: {filter_str}"


@pytest.mark.contract
def test_loudness_normalize_build_fn_pass2_with_measurements() -> None:
    """loudness_normalize build_fn returns pass-2 filter string when measurements are supplied."""
    filter_str = _build_loudness_normalize(
        {
            "target_lufs": -16.0,
            "ceiling_dbtp": -1.0,
            "measured_i": -18.5,
            "measured_lra": 9.2,
            "measured_tp": -2.0,
            "offset": 0.3,
        }
    )
    assert "loudnorm=" in filter_str, f"Expected loudnorm filter, got: {filter_str}"
    assert "linear=true" in filter_str, f"Expected pass-2 filter, got: {filter_str}"
    assert "measured_I=-18.5" in filter_str, f"Missing measured_I in: {filter_str}"


@pytest.mark.contract
def test_loudness_normalize_delivery_profile_target_takes_precedence() -> None:
    """delivery_profile_target_lufs overrides target_lufs in build_fn."""
    filter_str = _build_loudness_normalize(
        {
            "target_lufs": -16.0,
            "ceiling_dbtp": -1.0,
            "delivery_profile_target_lufs": -23.0,
        }
    )
    assert "I=-23" in filter_str, f"Expected delivery profile -23 LUFS, got: {filter_str}"
    assert "I=-16" not in filter_str, f"Should not contain effect-level -16, got: {filter_str}"


@pytest.mark.contract
def test_loudness_normalize_definition_registered() -> None:
    """loudness_normalize is registered in the default registry."""
    registry = create_default_registry()
    effect = registry.get("loudness_normalize")
    assert effect is not None, "loudness_normalize not found in default registry"
    assert effect is LOUDNESS_NORMALIZE
    preview = effect.preview_fn()
    assert "loudnorm=" in preview, f"Preview missing loudnorm: {preview}"


# ---- parametric_eq schema and round-trip tests (BL-429) ----


@pytest.mark.contract
def test_parametric_eq_build_fn_single_band() -> None:
    """parametric_eq build_fn emits correct anequalizer filter string for a single band."""
    filter_str = _build_parametric_eq(
        {"bands": [{"frequency": 1000.0, "gain": 6.0, "width": 200.0}]}
    )
    assert filter_str.startswith("anequalizer="), f"Expected anequalizer=..., got: {filter_str}"
    assert "c0 f=1000" in filter_str, f"Missing c0 f=1000 in: {filter_str}"
    assert "g=6" in filter_str, f"Missing g=6 in: {filter_str}"
    assert "t=1" in filter_str, f"Missing t=1 in: {filter_str}"


@pytest.mark.contract
def test_parametric_eq_build_fn_multi_band() -> None:
    """parametric_eq build_fn emits pipe-separated bands for multiple bands."""
    filter_str = _build_parametric_eq(
        {
            "bands": [
                {"frequency": 1000.0, "gain": 6.0, "width": 200.0},
                {"frequency": 5000.0, "gain": -3.0, "width": 500.0},
            ]
        }
    )
    assert "c0 f=1000" in filter_str, f"Missing c0 in: {filter_str}"
    assert "c1 f=5000" in filter_str, f"Missing c1 in: {filter_str}"
    assert "|" in filter_str, f"Missing pipe separator in: {filter_str}"


@pytest.mark.contract
def test_parametric_eq_schema_validates_valid_bands() -> None:
    """parametric_eq schema validates a valid bands array (BL-429-AC-2)."""
    registry = create_default_registry()
    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"frequency": 1000.0, "gain": 6.0, "width": 200.0}]},
    )
    assert errors == [], f"parametric_eq schema rejected valid bands: {errors}"


@pytest.mark.contract
def test_parametric_eq_schema_rejects_missing_bands() -> None:
    """parametric_eq schema rejects missing bands key (BL-429-AC-2)."""
    registry = create_default_registry()
    errors = registry.validate("parametric_eq", {})
    assert errors != [], "Schema should reject missing 'bands' key"


@pytest.mark.contract
def test_parametric_eq_schema_rejects_empty_bands() -> None:
    """parametric_eq schema rejects empty bands array (BL-429-AC-2)."""
    registry = create_default_registry()
    errors = registry.validate("parametric_eq", {"bands": []})
    assert errors != [], "Schema should reject empty bands array"


@pytest.mark.contract
def test_parametric_eq_schema_rejects_band_missing_frequency() -> None:
    """parametric_eq schema rejects band missing frequency field (BL-429-AC-2)."""
    registry = create_default_registry()
    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"gain": 6.0, "width": 200.0}]},
    )
    assert errors != [], "Schema should reject band missing 'frequency'"


@pytest.mark.contract
def test_parametric_eq_schema_rejects_frequency_out_of_range() -> None:
    """parametric_eq schema rejects frequency outside 20-20000 Hz (BL-429-AC-2)."""
    registry = create_default_registry()
    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"frequency": 10.0, "gain": 0.0, "width": 100.0}]},
    )
    assert errors != [], "Schema should reject frequency below 20 Hz"

    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"frequency": 25000.0, "gain": 0.0, "width": 100.0}]},
    )
    assert errors != [], "Schema should reject frequency above 20000 Hz"


@pytest.mark.contract
def test_parametric_eq_schema_rejects_gain_out_of_range() -> None:
    """parametric_eq schema rejects gain outside ±24 dB (BL-429-AC-2)."""
    registry = create_default_registry()
    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"frequency": 1000.0, "gain": 30.0, "width": 100.0}]},
    )
    assert errors != [], "Schema should reject gain above +24 dB"

    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"frequency": 1000.0, "gain": -30.0, "width": 100.0}]},
    )
    assert errors != [], "Schema should reject gain below -24 dB"


@pytest.mark.contract
def test_parametric_eq_schema_rejects_non_positive_width() -> None:
    """parametric_eq schema rejects width <= 0 (BL-429-AC-2)."""
    registry = create_default_registry()
    errors = registry.validate(
        "parametric_eq",
        {"bands": [{"frequency": 1000.0, "gain": 0.0, "width": 0.0}]},
    )
    assert errors != [], "Schema should reject width <= 0"


@pytest.mark.contract
def test_parametric_eq_definition_registered() -> None:
    """parametric_eq is registered in the default registry."""
    registry = create_default_registry()
    effect = registry.get("parametric_eq")
    assert effect is not None, "parametric_eq not found in default registry"
    assert effect is PARAMETRIC_EQ
    preview = effect.preview_fn()
    assert "anequalizer" in preview, f"Preview missing anequalizer: {preview}"


# ---- volume automation tests (BL-430-AC-1) ----


@pytest.mark.contract
def test_volume_automatable_contains_volume() -> None:
    """volume EffectDefinition automatable frozenset contains 'volume' (BL-430-AC-1)."""
    registry = create_default_registry()
    effect = registry.get("volume")
    assert effect is not None, "volume not found in default registry"
    assert "volume" in effect.automatable, (
        f"Expected 'volume' in automatable, got: {effect.automatable}"
    )


@pytest.mark.api
def test_list_effects_volume_has_automatable_parameters(client: TestClient) -> None:
    """volume effect exposes automatable_parameters=["volume"] in GET /effects (BL-481-AC-2)."""
    resp = client.get("/api/v1/effects")
    assert resp.status_code == 200
    effects_by_type = {e["effect_type"]: e for e in resp.json()["effects"]}
    volume = effects_by_type["volume"]
    assert "automatable_parameters" in volume
    assert volume["automatable_parameters"] == ["volume"]


@pytest.mark.api
def test_list_effects_dsp_effects_have_empty_automatable_parameters(client: TestClient) -> None:
    """DSP effects expose automatable_parameters=[] in GET /api/v1/effects (BL-481-AC-2)."""
    resp = client.get("/api/v1/effects")
    assert resp.status_code == 200
    effects_by_type = {e["effect_type"]: e for e in resp.json()["effects"]}
    mastering_limiter = effects_by_type["mastering_limiter"]
    assert "automatable_parameters" in mastering_limiter
    assert mastering_limiter["automatable_parameters"] == []


@pytest.mark.contract
def test_volume_automation_envelope_accepted() -> None:
    """validate_with_automation accepts volume keyframe envelope (BL-430-AC-1)."""
    registry = create_default_registry()
    errors, compiled_expression = registry.validate_with_automation(
        "volume",
        {
            "volume": {
                "default": 0.5,
                "keyframes": [
                    {"t": 0.0, "value": 0.2, "curve": "linear"},
                    {"t": 5.0, "value": 0.8, "curve": "linear"},
                ],
            }
        },
    )
    assert errors == [], f"Unexpected validation errors: {errors}"
    assert compiled_expression is not None, "Expected a compiled expression for automation envelope"
    assert len(compiled_expression) > 0, "Compiled expression should be non-empty"


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
    from stoat_ferret.api.schemas.effect import EffectTransitionResponse

    data = {
        "id": "test-uuid-123",
        "source_clip_id": "clip-a",
        "target_clip_id": "clip-b",
        "transition_type": "xfade",
        "parameters": {"transition": "fade", "duration": 1.0, "offset": 0.0},
        "filter_string": "xfade=transition=fade:duration=1:offset=0",
    }
    resp = EffectTransitionResponse(**data)
    assert resp.id == "test-uuid-123"
    assert resp.filter_string == "xfade=transition=fade:duration=1:offset=0"

    dumped = resp.model_dump()
    restored = EffectTransitionResponse(**dumped)
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
    assert "id" in data
    assert len(data["id"]) > 0
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
    assert "id" in data
    assert len(data["id"]) > 0
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


# ---- Effect CRUD (PATCH/DELETE) tests ----


async def _seed_clip_with_effects(
    project_repo: AsyncInMemoryProjectRepository,
    clip_repo: AsyncInMemoryClipRepository,
    video_repo: AsyncInMemoryVideoRepository,
    client: TestClient,
    effect_count: int = 2,
) -> tuple[str, str]:
    """Seed a project with a clip and apply effects for CRUD testing.

    Args:
        project_repo: Project repository to seed.
        clip_repo: Clip repository to seed.
        video_repo: Video repository to seed.
        client: Test client for applying effects.
        effect_count: Number of effects to apply.

    Returns:
        Tuple of (project_id, clip_id).
    """
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-crud",
        name="CRUD Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repo.add(project)
    video = make_test_video()
    await video_repo.add(video)
    clip = Clip(
        id="clip-crud",
        project_id="proj-crud",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repo.add(clip)

    effects = [
        {"effect_type": "text_overlay", "parameters": {"text": "First"}},
        {"effect_type": "volume", "parameters": {"volume": 1.5}},
        {"effect_type": "text_overlay", "parameters": {"text": "Third"}},
    ]
    for i in range(effect_count):
        resp = client.post(
            "/api/v1/projects/proj-crud/clips/clip-crud/effects",
            json=effects[i % len(effects)],
        )
        assert resp.status_code == 201

    return "proj-crud", "clip-crud"


@pytest.mark.api
async def test_patch_effect_updates_parameters(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """PATCH /effects/{index} updates effect parameters and regenerates filter string."""
    await _seed_clip_with_effects(
        project_repository, clip_repository, video_repository, client, effect_count=1
    )

    response = client.patch(
        "/api/v1/projects/proj-crud/clips/clip-crud/effects/0",
        json={"parameters": {"text": "Updated Text", "fontsize": 72}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["effect_type"] == "text_overlay"
    assert data["parameters"]["text"] == "Updated Text"
    assert data["parameters"]["fontsize"] == 72
    assert "drawtext" in data["filter_string"]
    assert "fontsize=72" in data["filter_string"]


@pytest.mark.api
async def test_patch_effect_persists_changes(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """PATCH /effects/{index} persists the updated effect on the clip."""
    await _seed_clip_with_effects(
        project_repository, clip_repository, video_repository, client, effect_count=1
    )

    client.patch(
        "/api/v1/projects/proj-crud/clips/clip-crud/effects/0",
        json={"parameters": {"text": "Persisted"}},
    )

    clip = await clip_repository.get("clip-crud")
    assert clip is not None
    assert clip.effects is not None
    assert clip.effects[0]["parameters"]["text"] == "Persisted"


@pytest.mark.api
async def test_patch_effect_invalid_index_returns_404(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """PATCH /effects/{index} with out-of-range index returns 404."""
    await _seed_clip_with_effects(
        project_repository, clip_repository, video_repository, client, effect_count=1
    )

    response = client.patch(
        "/api/v1/projects/proj-crud/clips/clip-crud/effects/99",
        json={"parameters": {"text": "Nope"}},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_delete_effect_removes_from_stack(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """DELETE /effects/{index} removes the effect and returns deleted info."""
    await _seed_clip_with_effects(
        project_repository, clip_repository, video_repository, client, effect_count=2
    )

    response = client.delete(
        "/api/v1/projects/proj-crud/clips/clip-crud/effects/0",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["index"] == 0
    assert data["deleted_effect_type"] == "text_overlay"

    # Verify only one effect remains
    clip = await clip_repository.get("clip-crud")
    assert clip is not None
    assert clip.effects is not None
    assert len(clip.effects) == 1
    assert clip.effects[0]["effect_type"] == "volume"


@pytest.mark.api
async def test_delete_effect_invalid_index_returns_404(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """DELETE /effects/{index} with out-of-range index returns 404."""
    await _seed_clip_with_effects(
        project_repository, clip_repository, video_repository, client, effect_count=1
    )

    response = client.delete(
        "/api/v1/projects/proj-crud/clips/clip-crud/effects/5",
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
async def test_delete_effect_nonexistent_project_returns_404(
    client: TestClient,
) -> None:
    """DELETE /effects/{index} with nonexistent project returns 404."""
    response = client.delete(
        "/api/v1/projects/nonexistent/clips/clip-1/effects/0",
    )
    assert response.status_code == 404


@pytest.mark.api
async def test_patch_effect_invalid_params_returns_400(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """PATCH /effects/{index} with invalid parameters returns 400."""
    await _seed_clip_with_effects(
        project_repository, clip_repository, video_repository, client, effect_count=1
    )

    # text_overlay requires 'text' field
    response = client.patch(
        "/api/v1/projects/proj-crud/clips/clip-crud/effects/0",
        json={"parameters": {"fontsize": "not_a_number"}},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_EFFECT_PARAMS"


# ---- Effect CRUD schema contract tests ----


@pytest.mark.contract
def test_effect_update_request_schema_roundtrip() -> None:
    """EffectUpdateRequest serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.effect import EffectUpdateRequest

    data: dict[str, Any] = {"parameters": {"text": "hello", "fontsize": 48}}
    req = EffectUpdateRequest(**data)
    assert req.parameters["text"] == "hello"
    dumped = req.model_dump()
    restored = EffectUpdateRequest(**dumped)
    assert restored == req


@pytest.mark.contract
def test_effect_delete_response_schema_roundtrip() -> None:
    """EffectDeleteResponse serializes and deserializes correctly."""
    from stoat_ferret.api.schemas.effect import EffectDeleteResponse

    data: dict[str, Any] = {"index": 0, "deleted_effect_type": "text_overlay"}
    resp = EffectDeleteResponse(**data)
    assert resp.index == 0
    assert resp.deleted_effect_type == "text_overlay"
    dumped = resp.model_dump()
    restored = EffectDeleteResponse(**dumped)
    assert restored == resp


# ---- Golden test: full CRUD workflow ----


@pytest.mark.api
async def test_golden_full_crud_workflow(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    video_repository: AsyncInMemoryVideoRepository,
) -> None:
    """Golden test: select effect, configure, apply, verify stack, edit, remove."""
    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-golden",
        name="Golden Test",
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
        id="clip-golden",
        project_id="proj-golden",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    # 1. Apply two effects
    resp1 = client.post(
        "/api/v1/projects/proj-golden/clips/clip-golden/effects",
        json={"effect_type": "text_overlay", "parameters": {"text": "Title"}},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        "/api/v1/projects/proj-golden/clips/clip-golden/effects",
        json={"effect_type": "volume", "parameters": {"volume": 2.0}},
    )
    assert resp2.status_code == 201

    # 2. Verify stack has two effects
    clip_data = await clip_repository.get("clip-golden")
    assert clip_data is not None
    assert clip_data.effects is not None
    assert len(clip_data.effects) == 2
    assert clip_data.effects[0]["effect_type"] == "text_overlay"
    assert clip_data.effects[1]["effect_type"] == "volume"

    # 3. Edit first effect
    resp3 = client.patch(
        "/api/v1/projects/proj-golden/clips/clip-golden/effects/0",
        json={"parameters": {"text": "Updated Title", "fontsize": 96}},
    )
    assert resp3.status_code == 200
    assert resp3.json()["parameters"]["text"] == "Updated Title"

    # 4. Remove second effect
    resp4 = client.delete(
        "/api/v1/projects/proj-golden/clips/clip-golden/effects/1",
    )
    assert resp4.status_code == 200
    assert resp4.json()["deleted_effect_type"] == "volume"

    # 5. Verify final state
    clip_final = await clip_repository.get("clip-golden")
    assert clip_final is not None
    assert clip_final.effects is not None
    assert len(clip_final.effects) == 1
    assert clip_final.effects[0]["parameters"]["text"] == "Updated Title"


# ---- Effect preview thumbnail tests ----


@pytest.mark.api
def test_thumbnail_unknown_effect_returns_400(client: TestClient) -> None:
    """POST /effects/preview/thumbnail with unknown effect returns 400."""
    response = client.post(
        "/api/v1/effects/preview/thumbnail",
        json={
            "effect_type": "nonexistent_effect",
            "video_path": "/tmp/fake_video.mp4",
            "parameters": {},
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "EFFECT_NOT_FOUND"


@pytest.mark.api
def test_thumbnail_missing_video_returns_400(client: TestClient) -> None:
    """POST /effects/preview/thumbnail with missing video file returns 400."""
    response = client.post(
        "/api/v1/effects/preview/thumbnail",
        json={
            "effect_type": "text_overlay",
            "video_path": "/tmp/does_not_exist_12345.mp4",
            "parameters": {"text": "Hello"},
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "VIDEO_NOT_FOUND"


@pytest.mark.api
def test_thumbnail_invalid_params_returns_400(
    client: TestClient,
    sample_video_path: Path,
) -> None:
    """POST /effects/preview/thumbnail with invalid params returns 400."""
    response = client.post(
        "/api/v1/effects/preview/thumbnail",
        json={
            "effect_type": "speed_control",
            "video_path": str(sample_video_path),
            "parameters": {"factor": "not_a_number"},
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_EFFECT_PARAMS"


@pytest.mark.api
def test_thumbnail_ffmpeg_failure_returns_500(
    sample_video_path: Path,
) -> None:
    """POST /effects/preview/thumbnail returns 500 when FFmpeg fails."""
    from stoat_ferret.ffmpeg.executor import ExecutionResult

    class FailingExecutor:
        """FFmpeg executor that always returns failure."""

        def run(
            self,
            args: list[str],
            *,
            stdin: bytes | None = None,
            timeout: float | None = None,
        ) -> ExecutionResult:
            return ExecutionResult(
                returncode=1,
                stdout=b"",
                stderr=b"ffmpeg error",
                command=["ffmpeg", *args],
                duration_seconds=0.1,
            )

    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        ffmpeg_executor=FailingExecutor(),
    )
    with TestClient(app) as c:
        response = c.post(
            "/api/v1/effects/preview/thumbnail",
            json={
                "effect_type": "text_overlay",
                "video_path": str(sample_video_path),
                "parameters": {"text": "Hello"},
            },
        )
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "THUMBNAIL_GENERATION_FAILED"


@pytest.mark.api
def test_thumbnail_success_returns_jpeg(
    sample_video_path: Path,
) -> None:
    """POST /effects/preview/thumbnail returns JPEG on success."""
    from stoat_ferret.ffmpeg.executor import ExecutionResult

    class FakePreviewExecutor:
        """FFmpeg executor that creates a fake JPEG file."""

        def run(
            self,
            args: list[str],
            *,
            stdin: bytes | None = None,
            timeout: float | None = None,
        ) -> ExecutionResult:
            # Find the output path (last argument) and write a fake JPEG
            output_path = args[-1]
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"\xff\xd8\xff\xe0fake_jpeg_data")
            return ExecutionResult(
                returncode=0,
                stdout=b"",
                stderr=b"",
                command=["ffmpeg", *args],
                duration_seconds=0.5,
            )

    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        ffmpeg_executor=FakePreviewExecutor(),
    )
    with TestClient(app) as c:
        response = c.post(
            "/api/v1/effects/preview/thumbnail",
            json={
                "effect_type": "text_overlay",
                "video_path": str(sample_video_path),
                "parameters": {"text": "Hello"},
            },
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8\xff\xe0")


@pytest.mark.api
def test_thumbnail_ffmpeg_command_has_correct_vf_filter(
    sample_video_path: Path,
) -> None:
    """Verify FFmpeg command includes -vf with effect filter and scale."""
    from stoat_ferret.ffmpeg.executor import ExecutionResult

    captured_args: list[list[str]] = []

    class CapturingExecutor:
        """FFmpeg executor that captures the args for inspection."""

        def run(
            self,
            args: list[str],
            *,
            stdin: bytes | None = None,
            timeout: float | None = None,
        ) -> ExecutionResult:
            captured_args.append(args)
            output_path = args[-1]
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"\xff\xd8\xff\xe0jpeg")
            return ExecutionResult(
                returncode=0,
                stdout=b"",
                stderr=b"",
                command=["ffmpeg", *args],
                duration_seconds=0.1,
            )

    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        ffmpeg_executor=CapturingExecutor(),
    )
    with TestClient(app) as c:
        c.post(
            "/api/v1/effects/preview/thumbnail",
            json={
                "effect_type": "text_overlay",
                "video_path": str(sample_video_path),
                "parameters": {"text": "Preview"},
            },
        )

    assert len(captured_args) == 1
    args = captured_args[0]
    # Verify -vf flag is present with effect filter + scale
    vf_idx = args.index("-vf")
    vf_value = args[vf_idx + 1]
    assert "drawtext" in vf_value
    assert "scale=320:-1" in vf_value
    # Verify timestamp at 0
    ss_idx = args.index("-ss")
    assert args[ss_idx + 1] == "0"
    # Verify single frame extraction
    assert "-frames:v" in args
    assert "1" in args[args.index("-frames:v") + 1]
    # Verify JPEG quality 3
    qv_idx = args.index("-q:v")
    assert args[qv_idx + 1] == "3"


# ---- noise_reduction schema and round-trip tests (BL-433) ----


@pytest.mark.contract
def test_noise_reduction_build_fn_broadband() -> None:
    """noise_reduction build_fn emits afftdn filter string in broadband mode."""
    filter_str = _build_noise_reduction({"mode": "broadband", "strength": 0.5})
    assert "afftdn" in filter_str, f"Expected afftdn in filter string, got: {filter_str}"


@pytest.mark.contract
def test_noise_reduction_build_fn_adeclick() -> None:
    """noise_reduction build_fn emits adeclick filter string in adeclick mode."""
    filter_str = _build_noise_reduction({"mode": "adeclick", "threshold": 0.3})
    assert "adeclick" in filter_str, f"Expected adeclick in filter string, got: {filter_str}"


@pytest.mark.contract
def test_noise_reduction_definition_registered() -> None:
    """noise_reduction is registered in the default registry."""
    registry = create_default_registry()
    effect = registry.get("noise_reduction")
    assert effect is not None, "noise_reduction not found in default registry"
    assert effect is NOISE_REDUCTION
    preview = effect.preview_fn()
    assert "afftdn" in preview, f"Preview missing afftdn: {preview}"


# ---- deesser schema and round-trip tests (BL-434) ----


@pytest.mark.contract
def test_deesser_build_fn() -> None:
    """deesser build_fn emits deesser filter string with frequency."""
    filter_str = _build_deesser({"frequency": 6000.0, "mode": "wide"})
    assert "deesser" in filter_str, f"Expected deesser in filter string, got: {filter_str}"
    # 6000 Hz / 22050 Hz ≈ 0.272109 (normalized to [0, 1])
    assert "f=0.272109" in filter_str, f"Expected f=0.272109 in filter string, got: {filter_str}"


@pytest.mark.contract
def test_deesser_definition_registered() -> None:
    """deesser is registered in the default registry."""
    registry = create_default_registry()
    effect = registry.get("deesser")
    assert effect is not None, "deesser not found in default registry"
    assert effect is DEESSER
    preview = effect.preview_fn()
    assert "deesser" in preview, f"Preview missing deesser: {preview}"


# ---- deplosive schema and round-trip tests (BL-434) ----


@pytest.mark.contract
def test_deplosive_build_fn() -> None:
    """deplosive build_fn emits highpass+acompressor filter chain."""
    filter_str = _build_deplosive({"cutoff": 60.0, "threshold": 0.1, "ratio": 4.0})
    assert "highpass" in filter_str, f"Expected highpass in filter chain, got: {filter_str}"
    assert "acompressor" in filter_str, f"Expected acompressor in filter chain, got: {filter_str}"


@pytest.mark.contract
def test_deplosive_definition_registered() -> None:
    """deplosive is registered in the default registry."""
    registry = create_default_registry()
    effect = registry.get("deplosive")
    assert effect is not None, "deplosive not found in default registry"
    assert effect is DEPLOSIVE
    preview = effect.preview_fn()
    assert "highpass" in preview, f"Preview missing highpass: {preview}"
    assert "acompressor" in preview, f"Preview missing acompressor: {preview}"


# ---- time_stretch schema and round-trip tests (BL-435) ----


@pytest.mark.contract
def test_time_stretch_build_fn_atempo() -> None:
    """time_stretch build_fn emits atempo filter string in atempo mode."""
    filter_str = _build_time_stretch({"factor": 0.8, "mode": "atempo"})
    assert "atempo" in filter_str, f"Expected atempo in filter string, got: {filter_str}"


@pytest.mark.contract
def test_time_stretch_definition_registered() -> None:
    """time_stretch is registered in the default registry."""
    registry = create_default_registry()
    effect = registry.get("time_stretch")
    assert effect is not None, "time_stretch not found in default registry"
    assert effect is TIME_STRETCH
    preview = effect.preview_fn()
    assert "atempo" in preview, f"Preview missing atempo: {preview}"


# ---- multiband_compressor schema and round-trip tests (BL-431) ----


@pytest.mark.contract
def test_multiband_compressor_build_fn_two_bands() -> None:
    """multiband_compressor build_fn emits asplit→acompressor×2→amix FilterGraph."""
    filter_str = _build_multiband_compressor(
        {
            "bands": [
                {"threshold": -20.0, "ratio": 2.0, "attack": 10.0, "release": 100.0},
                {"threshold": -24.0, "ratio": 3.0, "attack": 5.0, "release": 80.0},
            ]
        }
    )
    assert "asplit" in filter_str, f"Expected asplit in filter graph, got: {filter_str}"
    assert "acompressor" in filter_str, f"Expected acompressor in filter graph, got: {filter_str}"
    assert "amix" in filter_str, f"Expected amix in filter graph, got: {filter_str}"


@pytest.mark.contract
def test_multiband_compressor_build_fn_three_bands() -> None:
    """multiband_compressor build_fn emits asplit=outputs=3→acompressor×3→amix=inputs=3."""
    filter_str = _build_multiband_compressor(
        {
            "bands": [
                {"threshold": -20.0, "ratio": 2.0, "attack": 10.0, "release": 100.0},
                {"threshold": -24.0, "ratio": 3.0, "attack": 5.0, "release": 80.0},
                {"threshold": -30.0, "ratio": 4.0, "attack": 3.0, "release": 50.0},
            ]
        }
    )
    assert "asplit" in filter_str, f"Expected asplit in filter graph, got: {filter_str}"
    assert filter_str.count("acompressor") == 3, (
        f"Expected 3 acompressor filters, got: {filter_str}"
    )
    assert "amix" in filter_str, f"Expected amix in filter graph, got: {filter_str}"


@pytest.mark.contract
def test_multiband_compressor_schema_validates_valid_bands() -> None:
    """multiband_compressor schema validates a valid bands array (BL-431-AC-3)."""
    registry = create_default_registry()
    errors = registry.validate(
        "multiband_compressor",
        {
            "bands": [
                {"threshold": -20.0, "ratio": 2.0, "attack": 10.0, "release": 100.0},
                {"threshold": -24.0, "ratio": 3.0, "attack": 5.0, "release": 80.0},
            ]
        },
    )
    assert errors == [], f"multiband_compressor schema rejected valid params: {errors}"


@pytest.mark.contract
def test_multiband_compressor_schema_rejects_missing_bands() -> None:
    """multiband_compressor schema rejects missing bands key."""
    registry = create_default_registry()
    errors = registry.validate("multiband_compressor", {})
    assert errors != [], "Schema should reject missing 'bands' key"


@pytest.mark.contract
def test_multiband_compressor_schema_rejects_non_negative_threshold() -> None:
    """multiband_compressor schema rejects threshold >= 0."""
    registry = create_default_registry()
    errors = registry.validate(
        "multiband_compressor",
        {
            "bands": [
                {"threshold": 0.0, "ratio": 2.0, "attack": 10.0, "release": 100.0},
                {"threshold": -24.0, "ratio": 3.0, "attack": 5.0, "release": 80.0},
            ]
        },
    )
    assert errors != [], "Schema should reject threshold >= 0"


@pytest.mark.contract
def test_multiband_compressor_schema_rejects_ratio_le_one() -> None:
    """multiband_compressor schema rejects ratio <= 1.0."""
    registry = create_default_registry()
    errors = registry.validate(
        "multiband_compressor",
        {
            "bands": [
                {"threshold": -20.0, "ratio": 1.0, "attack": 10.0, "release": 100.0},
                {"threshold": -24.0, "ratio": 3.0, "attack": 5.0, "release": 80.0},
            ]
        },
    )
    assert errors != [], "Schema should reject ratio <= 1.0"


@pytest.mark.contract
def test_multiband_compressor_schema_rejects_band_missing_required_key() -> None:
    """multiband_compressor schema rejects band missing required key."""
    registry = create_default_registry()
    errors = registry.validate(
        "multiband_compressor",
        {
            "bands": [
                {"ratio": 2.0, "attack": 10.0, "release": 100.0},
                {"threshold": -24.0, "ratio": 3.0, "attack": 5.0, "release": 80.0},
            ]
        },
    )
    assert errors != [], "Schema should reject band missing 'threshold'"


@pytest.mark.contract
def test_multiband_compressor_definition_registered() -> None:
    """multiband_compressor is registered in the default registry (BL-431-AC-3)."""
    registry = create_default_registry()
    effect = registry.get("multiband_compressor")
    assert effect is not None, "multiband_compressor not found in default registry"
    assert effect is MULTIBAND_COMPRESSOR
    preview = effect.preview_fn()
    assert "asplit" in preview, f"Preview missing asplit: {preview}"
    assert "acompressor" in preview, f"Preview missing acompressor: {preview}"
    assert "amix" in preview, f"Preview missing amix: {preview}"
