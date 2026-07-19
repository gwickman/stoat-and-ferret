# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Effect discovery and application endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from prometheus_client import Counter

from stoat_ferret.api.schemas.clip import ClipEffectsResponse
from stoat_ferret.api.schemas.effect import (
    EffectApplyRequest,
    EffectApplyResponse,
    EffectDeleteResponse,
    EffectListResponse,
    EffectPreviewRequest,
    EffectPreviewResponse,
    EffectResponse,
    EffectThumbnailRequest,
    EffectTransitionResponse,
    EffectUpdateRequest,
    ParameterSchemaResponse,
    TransitionRequest,
)
from stoat_ferret.api.services.thumbnail import ThumbnailService
from stoat_ferret.db.clip_repository import AsyncClipRepository, AsyncSQLiteClipRepository
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.effects.definitions import EffectDefinition, create_default_registry
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.ffmpeg.executor import FFmpegExecutor, RealFFmpegExecutor
from stoat_ferret_core import parameter_schemas_from_dict

logger = structlog.get_logger(__name__)

effect_applications_total = Counter(
    "stoat_ferret_effect_applications_total",
    "Total effect applications by type",
    ["effect_type"],
)
transition_applications_total = Counter(
    "stoat_ferret_transition_applications_total",
    "Total transition applications by type",
    ["transition_type"],
)

router = APIRouter(prefix="/api/v1", tags=["effects"])

_default_registry: EffectRegistry | None = None


async def get_effect_registry(request: Request) -> EffectRegistry:
    """Get effect registry from app state.

    Falls back to a default registry if not injected via create_app().

    Args:
        request: The incoming HTTP request.

    Returns:
        The effect registry instance.
    """
    registry: EffectRegistry | None = getattr(request.app.state, "effect_registry", None)
    if registry is not None:
        return registry

    # Fallback: create default registry on first use
    global _default_registry  # noqa: PLW0603
    if _default_registry is None:
        _default_registry = create_default_registry()
    return _default_registry


async def _get_project_repository(request: Request) -> AsyncProjectRepository:
    """Get project repository from app state."""
    repo: AsyncProjectRepository | None = getattr(request.app.state, "project_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteProjectRepository(request.app.state.db)


async def _get_clip_repository(request: Request) -> AsyncClipRepository:
    """Get clip repository from app state."""
    repo: AsyncClipRepository | None = getattr(request.app.state, "clip_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteClipRepository(request.app.state.db)


async def _get_thumbnail_service(request: Request) -> ThumbnailService:
    """Get or create a ThumbnailService for effect preview thumbnails."""
    service: ThumbnailService | None = getattr(request.app.state, "effect_thumbnail_service", None)
    if service is not None:
        return service

    executor: FFmpegExecutor = (
        getattr(request.app.state, "ffmpeg_executor", None) or RealFFmpegExecutor()
    )
    from stoat_ferret.api.settings import get_settings

    settings = get_settings()
    return ThumbnailService(executor=executor, thumbnail_dir=settings.thumbnail_dir)


RegistryDep = Annotated[EffectRegistry, Depends(get_effect_registry)]
ProjectRepoDep = Annotated[AsyncProjectRepository, Depends(_get_project_repository)]
ClipRepoDep = Annotated[AsyncClipRepository, Depends(_get_clip_repository)]
ThumbnailDep = Annotated[ThumbnailService, Depends(_get_thumbnail_service)]


def _resolve_effect_helper(
    registry: EffectRegistry,
    effect_type: str,
    *,
    include_valid_types: bool = False,
) -> EffectDefinition:
    """Resolve effect from registry, raising 400 if not found.

    Args:
        registry: Effect registry to look up the definition.
        effect_type: Effect type identifier.
        include_valid_types: When True, includes valid_effect_types list in 404 detail.

    Returns:
        The matching EffectDefinition.

    Raises:
        HTTPException: 400 if effect type is not registered.
    """
    definition = registry.get(effect_type)
    if definition is None:
        detail: dict[str, Any] = {
            "code": "EFFECT_NOT_FOUND",
            "message": f"Unknown effect type: {effect_type}",
        }
        if include_valid_types:
            detail["valid_effect_types"] = [t for t, _ in registry.list_all()]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
    return definition


def _validate_params_helper(
    registry: EffectRegistry,
    effect_type: str,
    params: dict[str, Any],
    *,
    include_errors_list: bool = True,
    log_on_failure: bool = False,
) -> str | None:
    """Validate effect parameters, raising 400 on failure.

    Args:
        registry: Effect registry used for validation.
        effect_type: Effect type identifier.
        params: Parameter dict to validate.
        include_errors_list: When True, includes per-field errors list in 400 detail.
        log_on_failure: When True, logs a warning before raising on validation failure.

    Returns:
        Compiled automation expression string if an envelope was processed, else None.

    Raises:
        HTTPException: 400 if parameters are invalid.
    """
    validation_errors, compiled_expression = registry.validate_with_automation(effect_type, params)
    if validation_errors:
        messages = [f"{e.path}: {e.message}" if e.path else e.message for e in validation_errors]
        if log_on_failure:
            logger.warning(
                "effect_preview_validation_failed",
                effect_type=effect_type,
                validation_errors=messages,
            )
        detail: dict[str, Any] = {
            "code": "INVALID_EFFECT_PARAMS",
            "message": "; ".join(messages),
        }
        if include_errors_list:
            detail["errors"] = [{"path": e.path, "message": e.message} for e in validation_errors]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
    return compiled_expression


def _flatten_automation_helper(params: dict[str, Any]) -> dict[str, Any]:
    """Flatten automation envelopes to scalar defaults for static filter builds.

    Args:
        params: Raw parameter dict, possibly containing automation envelopes.

    Returns:
        Parameter dict with envelope dicts replaced by their default scalar values.
    """
    return {
        name: (
            value.get("default", 0.0) if isinstance(value, dict) and "keyframes" in value else value
        )
        for name, value in params.items()
    }


def _build_filter_helper(
    registry: EffectRegistry,
    definition: EffectDefinition,
    effect_type: str,
    params: dict[str, Any],
    compiled_expression: str | None,
    *,
    force_scalar: bool = False,
) -> str:
    """Build FFmpeg filter string, using automation or scalar path.

    Args:
        registry: Effect registry for automation filter string construction.
        definition: Resolved effect definition with build_fn.
        effect_type: Effect type identifier.
        params: Raw parameter dict.
        compiled_expression: Compiled automation expression, or None for scalar.
        force_scalar: When True, always use the scalar-default path (thumbnail variant).

    Returns:
        FFmpeg filter string.

    Raises:
        HTTPException: 400 if the build function raises.
    """
    if not force_scalar and compiled_expression is not None:
        return registry.build_automation_filter_string(effect_type, compiled_expression)
    scalar_params = _flatten_automation_helper(params)
    try:
        return definition.build_fn(scalar_params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_EFFECT_PARAMS",
                "message": str(e),
            },
        ) from None


@router.get("/effects", response_model=EffectListResponse)
async def list_effects(registry: RegistryDep) -> EffectListResponse:
    """List all available effects with metadata, schemas, and previews.

    Returns:
        List of all registered effects with their parameter schemas,
        AI hints, filter preview strings, structured parameter list,
        AI summary, and example prompt.
    """
    effects = []
    for effect_type, definition in registry.list_all():
        parameters = [
            ParameterSchemaResponse(
                name=p.name,
                param_type=p.param_type,
                default_value=p.default_value,
                min_value=p.min_value,
                max_value=p.max_value,
                enum_values=p.enum_values,
                description=p.description,
                ai_hint=p.ai_hint,
            )
            for p in parameter_schemas_from_dict(definition.parameter_schema, definition.ai_hints)
        ]
        effects.append(
            EffectResponse(
                effect_type=effect_type,
                name=definition.name,
                description=definition.description,
                parameter_schema=definition.parameter_schema,
                ai_hints=definition.ai_hints,
                filter_preview=definition.preview_fn(),
                parameters=parameters,
                ai_summary=definition.ai_summary,
                example_prompt=definition.example_prompt,
                automatable_parameters=sorted(definition.automatable),
            )
        )
    return EffectListResponse(effects=effects, total=len(effects))


@router.post("/effects/preview", response_model=EffectPreviewResponse)
async def preview_effect(
    request: EffectPreviewRequest,
    registry: RegistryDep,
) -> EffectPreviewResponse:
    """Preview the filter string an effect would generate without applying it.

    Validates the effect type and parameters, then returns the generated
    FFmpeg filter string.

    Args:
        request: Effect preview request with type and parameters.
        registry: Effect registry dependency.

    Returns:
        The effect type and generated filter string.

    Raises:
        HTTPException: 400 if effect type unknown or parameters invalid.
    """
    definition = _resolve_effect_helper(registry, request.effect_type)
    compiled_expression = _validate_params_helper(
        registry,
        request.effect_type,
        request.parameters,
        include_errors_list=True,
        log_on_failure=True,
    )
    filter_string = _build_filter_helper(
        registry, definition, request.effect_type, request.parameters, compiled_expression
    )
    return EffectPreviewResponse(
        effect_type=request.effect_type,
        filter_string=filter_string,
    )


@router.post("/effects/preview/thumbnail")
async def preview_effect_thumbnail(
    request: EffectThumbnailRequest,
    registry: RegistryDep,
    thumbnail_service: ThumbnailDep,
) -> FileResponse:
    """Generate a thumbnail showing an effect applied to a video frame.

    Extracts the first frame from the specified video, applies the effect
    filter, scales to 320px width, and returns a JPEG image.

    Args:
        request: Thumbnail request with effect name, video path, and parameters.
        registry: Effect registry dependency.
        thumbnail_service: Thumbnail service dependency.

    Returns:
        JPEG image response.

    Raises:
        HTTPException: 400 if effect unknown, parameters invalid, or video missing.
            500 if FFmpeg thumbnail generation fails.
    """
    definition = _resolve_effect_helper(registry, request.effect_type)

    # Validate video path exists
    video_path = Path(request.video_path)
    if not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VIDEO_NOT_FOUND",
                "message": f"Video file not found: {request.video_path}",
            },
        )

    # Validate parameters (automation envelopes accepted; expression discarded for thumbnail)
    compiled_expression = _validate_params_helper(
        registry, request.effect_type, request.parameters, include_errors_list=False
    )
    # Build filter string using scalar defaults for the visual frame (never automation path)
    filter_string = _build_filter_helper(
        registry,
        definition,
        request.effect_type,
        request.parameters,
        compiled_expression,
        force_scalar=True,
    )

    # Generate thumbnail
    output_path = await thumbnail_service.generate_effect_preview(
        video_path=request.video_path,
        effect_filter=filter_string,
    )
    if output_path is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "THUMBNAIL_GENERATION_FAILED",
                "message": "Failed to generate effect preview thumbnail",
            },
        )

    return FileResponse(output_path, media_type="image/jpeg")


@router.get(
    "/projects/{project_id}/clips/{clip_id}/effects",
    response_model=ClipEffectsResponse,
)
async def get_clip_effects(
    project_id: str,
    clip_id: str,
    clip_repo: ClipRepoDep,
) -> ClipEffectsResponse:
    """Get effects applied to a clip.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        clip_repo: Clip repository dependency.

    Returns:
        Applied effects list for the clip (empty list when no effects).

    Raises:
        HTTPException: 404 if clip not found or belongs to different project.
    """
    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )
    return ClipEffectsResponse(effects=clip.effects or [])


@router.post(
    "/projects/{project_id}/clips/{clip_id}/effects",
    response_model=EffectApplyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_effect_to_clip(
    project_id: str,
    clip_id: str,
    request: EffectApplyRequest,
    registry: RegistryDep,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> EffectApplyResponse:
    """Apply an effect to a clip.

    Validates the effect type via the registry, validates parameters against
    the JSON schema, generates a filter string via the registered build function,
    and stores the effect configuration on the clip.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        request: Effect application request with type and parameters.
        registry: Effect registry dependency.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        The applied effect with generated filter string.

    Raises:
        HTTPException: 404 if project or clip not found, 400 if effect type
            unknown or parameters invalid.
    """
    # Validate project exists
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    # Validate clip exists and belongs to project
    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )

    # Validate effect type via registry
    definition = _resolve_effect_helper(registry, request.effect_type, include_valid_types=True)

    # Buffer-limit guard for memory-intensive effects (BL-444).
    if request.effect_type == "reverse":
        from stoat_ferret.api.settings import get_settings

        settings = get_settings()
        max_s = settings.reverse_max_duration_s
        clip_s = (clip.out_point - clip.in_point) / project.output_fps
        if clip_s > max_s:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "error": "clip_too_long",
                    "max_s": max_s,
                    "clip_s": clip_s,
                },
            )

    # Frame-number bounds check for freeze_frame (BL-449).
    if request.effect_type == "freeze_frame":
        frame_number = int(request.parameters.get("frame_number", 0))
        clip_duration_in_frames = clip.out_point - clip.in_point
        if frame_number >= clip_duration_in_frames:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "error": "frame_number_out_of_range",
                    "frame_number": frame_number,
                    "clip_duration_in_frames": clip_duration_in_frames,
                },
            )

    # Validate parameters against JSON schema (envelopes bypass JSON schema).
    compiled_expression = _validate_params_helper(registry, request.effect_type, request.parameters)
    # Generate filter string via registered build function.
    # For automation envelopes, use the automation-aware filter string with :eval=frame.
    filter_string = _build_filter_helper(
        registry, definition, request.effect_type, request.parameters, compiled_expression
    )

    # Window range-gating (BL-446): conflict check, then append enable clause.
    filter_preview: str | None = None
    if request.window is not None:
        if "enable=" in filter_string:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "window_conflicts_with_builtin_enable",
                    "message": (
                        "Effect output already contains an enable clause; window cannot be applied"
                    ),
                },
            )
        filter_string = (
            f"{filter_string}:enable='between(t,{request.window.start_s},{request.window.end_s})'"
        )
        filter_preview = filter_string
    elif compiled_expression is not None:
        filter_preview = compiled_expression

    # Store effect on clip
    effect_entry: dict[str, Any] = {
        "effect_type": request.effect_type,
        "parameters": request.parameters,
        "filter_string": filter_string,
    }
    if request.window is not None:
        effect_entry["window"] = {
            "start_s": request.window.start_s,
            "end_s": request.window.end_s,
        }
    if clip.effects is None:
        clip.effects = []
    clip.effects.append(effect_entry)
    clip.updated_at = datetime.now(timezone.utc)
    await clip_repo.update(clip)

    effect_applications_total.labels(effect_type=request.effect_type).inc()

    logger.info(
        "effect_applied",
        project_id=project_id,
        clip_id=clip_id,
        effect_type=request.effect_type,
    )

    return EffectApplyResponse(
        effect_type=request.effect_type,
        parameters=request.parameters,
        filter_string=filter_string,
        filter_preview=filter_preview,
    )


@router.patch(
    "/projects/{project_id}/clips/{clip_id}/effects/{index}",
    response_model=EffectApplyResponse,
)
async def update_clip_effect(
    project_id: str,
    clip_id: str,
    index: int,
    request: EffectUpdateRequest,
    registry: RegistryDep,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> EffectApplyResponse:
    """Update an effect at a specific index on a clip.

    Validates the index is within bounds, validates the new parameters
    against the effect's JSON schema, regenerates the filter string,
    and updates the effect in-place.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        index: Zero-based index of the effect in the clip's effects list.
        request: Updated parameters for the effect.
        registry: Effect registry dependency.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        The updated effect with regenerated filter string.

    Raises:
        HTTPException: 404 if project, clip, or effect index not found,
            400 if parameters invalid.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )

    effects = clip.effects or []
    if index < 0 or index >= len(effects):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Effect index {index} out of range (0..{len(effects) - 1})",
            },
        )

    effect_entry = effects[index]
    effect_type = effect_entry["effect_type"]

    definition = _resolve_effect_helper(registry, effect_type)
    compiled_expression = _validate_params_helper(registry, effect_type, request.parameters)
    filter_string = _build_filter_helper(
        registry, definition, effect_type, request.parameters, compiled_expression
    )

    effects[index] = {
        "effect_type": effect_type,
        "parameters": request.parameters,
        "filter_string": filter_string,
    }
    clip.updated_at = datetime.now(timezone.utc)
    await clip_repo.update(clip)

    logger.info(
        "effect_updated",
        project_id=project_id,
        clip_id=clip_id,
        effect_type=effect_type,
        index=index,
    )

    return EffectApplyResponse(
        effect_type=effect_type,
        parameters=request.parameters,
        filter_string=filter_string,
        filter_preview=compiled_expression,
    )


@router.delete(
    "/projects/{project_id}/clips/{clip_id}/effects/{index}",
    response_model=EffectDeleteResponse,
)
async def delete_clip_effect(
    project_id: str,
    clip_id: str,
    index: int,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> EffectDeleteResponse:
    """Remove an effect at a specific index from a clip.

    Validates the index is within bounds, removes the effect from the
    clip's effects list, and persists the change.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        index: Zero-based index of the effect to remove.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        The deleted effect index and type.

    Raises:
        HTTPException: 404 if project, clip, or effect index not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )

    effects = clip.effects or []
    if index < 0 or index >= len(effects):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Effect index {index} out of range (0..{len(effects) - 1})",
            },
        )

    removed = effects.pop(index)
    clip.updated_at = datetime.now(timezone.utc)
    await clip_repo.update(clip)

    logger.info(
        "effect_deleted",
        project_id=project_id,
        clip_id=clip_id,
        effect_type=removed["effect_type"],
        index=index,
    )

    return EffectDeleteResponse(
        index=index,
        deleted_effect_type=removed["effect_type"],
    )


@router.post(
    "/projects/{project_id}/effects/transition",
    response_model=EffectTransitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_transition(
    project_id: str,
    request: TransitionRequest,
    registry: RegistryDep,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> EffectTransitionResponse:
    """Apply a transition between two adjacent clips.

    Validates that both clips exist and are adjacent in the project timeline,
    generates the FFmpeg filter string via the effect registry, and stores
    the transition in the project model.

    Args:
        project_id: The unique project identifier.
        request: Transition request with source/target clips, type, and parameters.
        registry: Effect registry dependency.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        The applied transition with generated filter string.

    Raises:
        HTTPException: 404 if project or clips not found, 400 if clips not adjacent
            or transition type unknown or parameters invalid.
    """
    # Validate project exists
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    # Same clip check
    if request.source_clip_id == request.target_clip_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SAME_CLIP",
                "message": "Source and target clips must be different",
            },
        )

    # Get all clips in the project timeline
    clips = await clip_repo.list_by_project(project_id)
    if not clips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_TIMELINE", "message": "Project timeline has no clips"},
        )

    # Find source and target clips
    clip_index: dict[str, int] = {c.id: i for i, c in enumerate(clips)}

    if request.source_clip_id not in clip_index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Clip {request.source_clip_id} not found",
            },
        )
    if request.target_clip_id not in clip_index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Clip {request.target_clip_id} not found",
            },
        )

    # Adjacency check: source must immediately precede target in timeline order
    source_idx = clip_index[request.source_clip_id]
    target_idx = clip_index[request.target_clip_id]
    if target_idx != source_idx + 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NOT_ADJACENT",
                "message": "Source and target clips are not adjacent in the timeline",
            },
        )

    # Validate transition type via registry
    definition = registry.get(request.transition_type)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EFFECT_NOT_FOUND",
                "message": f"Unknown transition type: {request.transition_type}",
            },
        )

    # Validate parameters against JSON schema
    validation_errors = registry.validate(request.transition_type, request.parameters)
    if validation_errors:
        messages = [f"{e.path}: {e.message}" if e.path else e.message for e in validation_errors]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_EFFECT_PARAMS",
                "message": "; ".join(messages),
                "errors": [{"path": e.path, "message": e.message} for e in validation_errors],
            },
        )

    # Generate filter string via registered build function
    try:
        filter_string = definition.build_fn(request.parameters)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_EFFECT_PARAMS",
                "message": str(e),
            },
        ) from None

    # Store transition in project model
    transition_id = str(uuid.uuid4())
    transition_entry: dict[str, Any] = {
        "id": transition_id,
        "source_clip_id": request.source_clip_id,
        "target_clip_id": request.target_clip_id,
        "transition_type": request.transition_type,
        "parameters": request.parameters,
        "filter_string": filter_string,
    }
    if project.transitions is None:
        project.transitions = []
    project.transitions.append(transition_entry)
    project.updated_at = datetime.now(timezone.utc)
    await project_repo.update(project)

    transition_applications_total.labels(transition_type=request.transition_type).inc()

    logger.info(
        "transition_applied",
        project_id=project_id,
        source_clip_id=request.source_clip_id,
        target_clip_id=request.target_clip_id,
        transition_type=request.transition_type,
    )

    return EffectTransitionResponse(
        id=transition_id,
        source_clip_id=request.source_clip_id,
        target_clip_id=request.target_clip_id,
        transition_type=request.transition_type,
        parameters=request.parameters,
        filter_string=filter_string,
    )
