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
    EffectListResponse,
    EffectResponse,
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
