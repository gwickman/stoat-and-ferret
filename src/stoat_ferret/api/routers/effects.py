"""Effect discovery and application endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from prometheus_client import Counter

from stoat_ferret.api.schemas.effect import (
    EffectApplyRequest,
    EffectApplyResponse,
    EffectDeleteResponse,
    EffectListResponse,
    EffectPreviewRequest,
    EffectPreviewResponse,
    EffectResponse,
    EffectUpdateRequest,
    TransitionRequest,
    TransitionResponse,
)
from stoat_ferret.db.clip_repository import AsyncClipRepository, AsyncSQLiteClipRepository
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.effects.definitions import create_default_registry
from stoat_ferret.effects.registry import EffectRegistry

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


RegistryDep = Annotated[EffectRegistry, Depends(get_effect_registry)]
ProjectRepoDep = Annotated[AsyncProjectRepository, Depends(_get_project_repository)]
ClipRepoDep = Annotated[AsyncClipRepository, Depends(_get_clip_repository)]


@router.get("/effects", response_model=EffectListResponse)
async def list_effects(registry: RegistryDep) -> EffectListResponse:
    """List all available effects with metadata, schemas, and previews.

    Returns:
        List of all registered effects with their parameter schemas,
        AI hints, and filter preview strings.
    """
    effects = []
    for effect_type, definition in registry.list_all():
        effects.append(
            EffectResponse(
                effect_type=effect_type,
                name=definition.name,
                description=definition.description,
                parameter_schema=definition.parameter_schema,
                ai_hints=definition.ai_hints,
                filter_preview=definition.preview_fn(),
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
    definition = registry.get(request.effect_type)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EFFECT_NOT_FOUND",
                "message": f"Unknown effect type: {request.effect_type}",
            },
        )

    validation_errors = registry.validate(request.effect_type, request.parameters)
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

    return EffectPreviewResponse(
        effect_type=request.effect_type,
        filter_string=filter_string,
    )


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
    definition = registry.get(request.effect_type)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EFFECT_NOT_FOUND",
                "message": f"Unknown effect type: {request.effect_type}",
            },
        )

    # Validate parameters against JSON schema
    validation_errors = registry.validate(request.effect_type, request.parameters)
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

    # Store effect on clip
    effect_entry: dict[str, Any] = {
        "effect_type": request.effect_type,
        "parameters": request.parameters,
        "filter_string": filter_string,
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

    definition = registry.get(effect_type)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EFFECT_NOT_FOUND",
                "message": f"Unknown effect type: {effect_type}",
            },
        )

    validation_errors = registry.validate(effect_type, request.parameters)
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
    response_model=TransitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_transition(
    project_id: str,
    request: TransitionRequest,
    registry: RegistryDep,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> TransitionResponse:
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
    transition_entry: dict[str, Any] = {
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

    return TransitionResponse(
        source_clip_id=request.source_clip_id,
        target_clip_id=request.target_clip_id,
        transition_type=request.transition_type,
        parameters=request.parameters,
        filter_string=filter_string,
    )
