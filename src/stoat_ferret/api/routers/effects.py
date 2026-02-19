"""Effect discovery and application endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

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


def _build_filter_string(effect_type: str, parameters: dict[str, Any]) -> str:
    """Build an FFmpeg filter string from effect type and parameters.

    Args:
        effect_type: The effect type identifier (e.g., "text_overlay").
        parameters: The effect parameters.

    Returns:
        The generated FFmpeg filter string.

    Raises:
        ValueError: If the parameters are invalid for the effect type.
    """
    if effect_type == "text_overlay":
        from stoat_ferret_core import DrawtextBuilder

        text = parameters.get("text", "")
        builder = DrawtextBuilder(text)

        if "fontsize" in parameters:
            builder = builder.fontsize(parameters["fontsize"])
        if "fontcolor" in parameters:
            builder = builder.fontcolor(parameters["fontcolor"])
        if "position" in parameters:
            margin = parameters.get("margin", 10)
            builder = builder.position(parameters["position"], margin=margin)
        if "font" in parameters:
            builder = builder.font(parameters["font"])

        f = builder.build()
        return str(f)

    if effect_type == "speed_control":
        from stoat_ferret_core import SpeedControl

        factor = parameters.get("factor", 2.0)
        sc = SpeedControl(factor)
        video_filter = sc.setpts_filter()
        audio_filters = sc.atempo_filters()
        parts = [str(video_filter)]
        parts.extend(str(af) for af in audio_filters)
        return "; ".join(parts)

    msg = f"Unknown effect type: {effect_type}"
    raise ValueError(msg)


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

    Validates the effect type via the registry, generates a filter string
    via the Rust builder, and stores the effect configuration on the clip.

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

    # Generate filter string via Rust builder
    try:
        filter_string = _build_filter_string(request.effect_type, request.parameters)
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
